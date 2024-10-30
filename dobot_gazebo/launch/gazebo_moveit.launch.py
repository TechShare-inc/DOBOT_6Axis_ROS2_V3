import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinsubstitution
import xacro
import yaml


def load_file(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as file:
            return file.read()
    except EnvironmentError:
        return None


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as file:
            return yaml.safe_load(file)
    except EnvironmentError:
        return None


def generate_launch_description():
    mane = os.getenv("DOBOT_TYPE")
    robot_name_in_model = f'{mane}_robot'
    package_name = 'cra_description'
    urdf_name = f"{mane}_robot.xacro"
    world_file_path = PathJoinsubstitution([
        get_package_share_directory('dobot_gazebo'), 
        'worlds', 
        'ur10.world'
    ])
    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('ros_gz_sim'), 'launch'), '/gz_sim.launch.py']),
                launch_arguments=[('gz_args', world_file_path)],
             )
    cra_description_path = os.path.join(
        get_package_share_directory(package_name))

    xacro_file = os.path.join(cra_description_path,
                              'urdf',
                              urdf_name)

    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    robot_description_config = doc.toxml()
    robot_description = {'robot_description': robot_description_config}

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    spawn_entity = Node(package='ros_gz_sim', executable='create',
                        arguments=['-topic', 'robot_description',
                                   '-name', robot_name_in_model],
                        output='screen')
    
    # コントローラの起動
    load_joint_state_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    load_joint_trajectory_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             f'{mane}_group_controller'],
        output='screen'
    )

    close_evt1 =  RegisterEventHandler( 
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[load_joint_state_controller],
            )
    )
    close_evt2 = RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=load_joint_state_controller,
                on_exit=[load_joint_trajectory_controller],
            )
    )

    return LaunchDescription([
      close_evt1,
      close_evt2,
      gazebo,
      node_robot_state_publisher,
      spawn_entity
    ])
