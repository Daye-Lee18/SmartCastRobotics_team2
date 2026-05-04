import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def _load_namespace(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file) or {}
    except FileNotFoundError:
        return ""

    namespace = config.get("namespace", "")
    return namespace.strip() if isinstance(namespace, str) else ""


def _launch_setup(context, *args, **kwargs):
    del args, kwargs

    config_path = LaunchConfiguration("robot_config_file").perform(context)
    cli_namespace = LaunchConfiguration("namespace").perform(context).strip()
    namespace = cli_namespace or _load_namespace(config_path)
    frame_prefix = f"{namespace}/" if namespace else ""

    return [
        IncludeLaunchDescription(
            FrontendLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("tat_bringup"),
                    "launch",
                    "bringup_robot.launch.xml",
                )
            ),
            launch_arguments={
                "namespace": namespace,
                "use_sim_time": LaunchConfiguration("use_sim_time").perform(context),
                "frame_prefix": frame_prefix,
                "wheel_radius": LaunchConfiguration("wheel_radius").perform(context),
                "wheel_separation": LaunchConfiguration("wheel_separation").perform(context),
                "odom_frame_id": f"{frame_prefix}odom",
                "base_frame_id": f"{frame_prefix}base_footprint",
                "lidar_frame_id": f"{frame_prefix}rplidar_link",
                "left_joint_name": f"{frame_prefix}l_wheel_joint",
                "right_joint_name": f"{frame_prefix}r_wheel_joint",
            }.items(),
        )
    ]


def generate_launch_description():
    default_config_file = os.path.join(
        get_package_share_directory("tat_bringup"),
        "config",
        "robot_config.yaml",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "robot_config_file",
                default_value=default_config_file,
                description="YAML file that provides the default namespace for this robot.",
            ),
            DeclareLaunchArgument(
                "namespace",
                default_value="",
                description="Optional namespace override. If empty, the value from robot_config_file is used.",
            ),
            DeclareLaunchArgument("use_sim_time", default_value="False"),
            DeclareLaunchArgument("wheel_radius", default_value="0.027"),
            DeclareLaunchArgument("wheel_separation", default_value="0.0961"),
            OpaqueFunction(function=_launch_setup),
        ]
    )
