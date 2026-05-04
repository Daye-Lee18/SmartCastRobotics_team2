from pathlib import Path

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from picamera2 import Picamera2
from rclpy.node import Node
from tf_transformations import quaternion_from_matrix


ARUCO_DICT = {
    'DICT_4X4_50': cv2.aruco.DICT_4X4_50,
    'DICT_4X4_100': cv2.aruco.DICT_4X4_100,
    'DICT_4X4_250': cv2.aruco.DICT_4X4_250,
    'DICT_4X4_1000': cv2.aruco.DICT_4X4_1000,
    'DICT_5X5_50': cv2.aruco.DICT_5X5_50,
    'DICT_5X5_100': cv2.aruco.DICT_5X5_100,
    'DICT_5X5_250': cv2.aruco.DICT_5X5_250,
    'DICT_5X5_1000': cv2.aruco.DICT_5X5_1000,
    'DICT_6X6_50': cv2.aruco.DICT_6X6_50,
    'DICT_6X6_100': cv2.aruco.DICT_6X6_100,
    'DICT_6X6_250': cv2.aruco.DICT_6X6_250,
    'DICT_6X6_1000': cv2.aruco.DICT_6X6_1000,
    'DICT_7X7_50': cv2.aruco.DICT_7X7_50,
    'DICT_7X7_100': cv2.aruco.DICT_7X7_100,
    'DICT_7X7_250': cv2.aruco.DICT_7X7_250,
    'DICT_7X7_1000': cv2.aruco.DICT_7X7_1000,
    'DICT_ARUCO_ORIGINAL': cv2.aruco.DICT_ARUCO_ORIGINAL,
}


class ArucoMarkerPoseNode(Node):
    def __init__(self):
        super().__init__('aruco_marker_pose_node')

        self.declare_parameter('target_pose_topic', '/detected_dock_pose')
        self.declare_parameter('camera_frame', 'front_camera_link')
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 10.0)
        self.declare_parameter('rotate_180', True)
        self.declare_parameter('orientation_yaw_offset', 0.0)
        self.declare_parameter('aruco_dictionary', 'DICT_5X5_100')
        self.declare_parameter('marker_length', 0.079)
        self.declare_parameter('target_marker_id', 23)
        self.declare_parameter('camera_matrix_path', '')
        self.declare_parameter('distortion_coeffs_path', '')

        self.target_pose_topic = self.get_parameter('target_pose_topic').value
        self.camera_frame = self.get_parameter('camera_frame').value
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = float(self.get_parameter('fps').value)
        self.rotate_180 = bool(self.get_parameter('rotate_180').value)
        self.orientation_yaw_offset = float(self.get_parameter('orientation_yaw_offset').value)
        self.marker_length = float(self.get_parameter('marker_length').value)
        self.target_marker_id = int(self.get_parameter('target_marker_id').value)

        dictionary_name = self.get_parameter('aruco_dictionary').value
        if dictionary_name not in ARUCO_DICT:
            raise ValueError(f'Unsupported ArUco dictionary: {dictionary_name}')
        self.detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(ARUCO_DICT[dictionary_name]),
            cv2.aruco.DetectorParameters(),
        )

        self.camera_matrix = self.load_matrix(self.get_parameter('camera_matrix_path').value)
        self.dist_coeffs = self.load_distortion(self.get_parameter('distortion_coeffs_path').value)

        if self.camera_matrix is None or self.dist_coeffs is None:
            raise RuntimeError('Calibration files are required for aruco_marker_pose_node')

        self.pose_pub = self.create_publisher(PoseStamped, self.target_pose_topic, 10)

        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_preview_configuration(
                main={'format': 'RGB888', 'size': (self.width, self.height)}
            )
        )
        self.picam2.start()

        period = 1.0 / self.fps if self.fps > 0.0 else 0.1
        self.timer = self.create_timer(period, self.detect_and_publish)

    def load_matrix(self, path):
        if not path:
            return None
        matrix_path = Path(path)
        if not matrix_path.exists():
            self.get_logger().error(f'camera_matrix_path does not exist: {path}')
            return None
        matrix = np.load(matrix_path)
        if matrix.shape != (3, 3):
            raise ValueError(f'camera matrix must be 3x3, got {matrix.shape}')
        return matrix.astype(np.float64)

    def load_distortion(self, path):
        if not path:
            return None
        dist_path = Path(path)
        if not dist_path.exists():
            self.get_logger().error(f'distortion_coeffs_path does not exist: {path}')
            return None
        return np.load(dist_path).reshape(-1).astype(np.float64)

    def detect_and_publish(self):
        frame = self.picam2.capture_array()
        if self.rotate_180:
            frame = frame[::-1, ::-1].copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        corners, ids, _ = self.detector.detectMarkers(gray)
        if ids is None or len(ids) == 0:
            return

        ids = ids.flatten().tolist()
        marker_index = self.select_marker_index(ids)
        if marker_index is None:
            return

        stamp = self.get_clock().now().to_msg()
        pose_msg = self.compute_pose(corners[marker_index], stamp)
        if pose_msg is None:
            return

        self.pose_pub.publish(pose_msg)

    def select_marker_index(self, ids):
        for index, marker_id in enumerate(ids):
            if marker_id == self.target_marker_id:
                return index
        return None

    def compute_pose(self, marker_corners, stamp):
        object_points = np.array([
            [-self.marker_length / 2.0, self.marker_length / 2.0, 0.0],
            [self.marker_length / 2.0, self.marker_length / 2.0, 0.0],
            [self.marker_length / 2.0, -self.marker_length / 2.0, 0.0],
            [-self.marker_length / 2.0, -self.marker_length / 2.0, 0.0],
        ], dtype=np.float32)

        try:
            success, rvec, tvec = cv2.solvePnP(
                object_points,
                marker_corners[0].astype(np.float32),
                self.camera_matrix,
                self.dist_coeffs,
                flags=cv2.SOLVEPNP_IPPE_SQUARE,
            )
        except cv2.error as exc:
            self.get_logger().warn(f'solvePnP failed: {exc}')
            return None

        if not success:
            return None

        rotation_matrix, _ = cv2.Rodrigues(rvec)
        ros_camera_rotation = self.cv_optical_to_ros_camera_link_rotation()
        ros_marker_rotation = ros_camera_rotation @ rotation_matrix
        ros_marker_rotation = self.rotation_about_z(self.orientation_yaw_offset) @ ros_marker_rotation
        ros_translation = ros_camera_rotation @ np.array(
            [float(tvec[0][0]), float(tvec[1][0]), float(tvec[2][0])],
            dtype=np.float64,
        )

        transform = np.eye(4, dtype=np.float64)
        transform[:3, :3] = ros_marker_rotation
        quat = quaternion_from_matrix(transform)

        pose_msg = PoseStamped()
        pose_msg.header.stamp = stamp
        pose_msg.header.frame_id = self.camera_frame
        pose_msg.pose.position.x = float(ros_translation[0])
        pose_msg.pose.position.y = float(ros_translation[1])
        pose_msg.pose.position.z = float(ros_translation[2])
        pose_msg.pose.orientation.x = float(quat[0])
        pose_msg.pose.orientation.y = float(quat[1])
        pose_msg.pose.orientation.z = float(quat[2])
        pose_msg.pose.orientation.w = float(quat[3])
        return pose_msg

    @staticmethod
    def cv_optical_to_ros_camera_link_rotation():
        return np.array(
            [
                [0.0, 0.0, 1.0],
                [-1.0, 0.0, 0.0],
                [0.0, -1.0, 0.0],
            ],
            dtype=np.float64,
        )

    @staticmethod
    def rotation_about_z(yaw):
        cos_yaw = np.cos(yaw)
        sin_yaw = np.sin(yaw)
        return np.array(
            [
                [cos_yaw, -sin_yaw, 0.0],
                [sin_yaw, cos_yaw, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def destroy_node(self):
        try:
            self.picam2.stop()
            self.picam2.close()
        except Exception:
            pass
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ArucoMarkerPoseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
