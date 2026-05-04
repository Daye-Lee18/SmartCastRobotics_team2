import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import ReplaceString, RewrittenYaml


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
    params_file = LaunchConfiguration("params_file").perform(context)
    source_params = ReplaceString(
        source_file=params_file,
        replacements={"<robot_namespace>": f"/{namespace}" if namespace else ""},
    )

    configured_params = source_params
    if namespace:
        frame_prefix = f"{namespace}/"
        configured_params = RewrittenYaml(
            source_file=source_params,
            root_key=namespace,
            param_rewrites={
                "amcl.ros__parameters.base_frame_id": f"{frame_prefix}base_footprint",
                "amcl.ros__parameters.odom_frame_id": f"{frame_prefix}odom",
                "bt_navigator.ros__parameters.robot_base_frame": f"{frame_prefix}base_link",
                "local_costmap.local_costmap.ros__parameters.global_frame": f"{frame_prefix}odom",
                "local_costmap.local_costmap.ros__parameters.robot_base_frame": f"{frame_prefix}base_footprint",
                "global_costmap.global_costmap.ros__parameters.robot_base_frame": f"{frame_prefix}base_footprint",
                "behavior_server.ros__parameters.local_frame": f"{frame_prefix}odom",
                "behavior_server.ros__parameters.robot_base_frame": f"{frame_prefix}base_footprint",
                "docking_server.ros__parameters.base_frame": f"{frame_prefix}base_footprint",
                "docking_server.ros__parameters.fixed_frame": f"{frame_prefix}odom",
            },
            convert_types=True,
        )

    return [
        IncludeLaunchDescription(
            FrontendLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("tat_navigation"),
                    "launch",
                    "bringup_launch.xml",
                )
            ),
            launch_arguments={
                "namespace": namespace,
                "map": LaunchConfiguration("map").perform(context),
                "use_sim_time": LaunchConfiguration("use_sim_time").perform(context),
                "params_file": configured_params,
                "autostart": LaunchConfiguration("autostart").perform(context),
                "container_name": LaunchConfiguration("container_name").perform(context),
                "use_composition": LaunchConfiguration("use_composition").perform(context),
                "use_respawn": LaunchConfiguration("use_respawn").perform(context),
                "log_level": LaunchConfiguration("log_level").perform(context),
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
            DeclareLaunchArgument("map", default_value=""),
            DeclareLaunchArgument(
                "params_file",
                default_value=os.path.join(
                    get_package_share_directory("tat_navigation"),
                    "params",
                    "nav2_params.yaml",
                ),
            ),
            DeclareLaunchArgument("use_sim_time", default_value="False"),
            DeclareLaunchArgument("autostart", default_value="True"),
            DeclareLaunchArgument("container_name", default_value="nav2_container"),
            DeclareLaunchArgument("use_composition", default_value="True"),
            DeclareLaunchArgument("use_respawn", default_value="False"),
            DeclareLaunchArgument("log_level", default_value="info"),
            OpaqueFunction(function=_launch_setup),
        ]
    )
