from setuptools import find_packages, setup
import glob
import os


package_name = 'aruco_node'


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob.glob(os.path.join('launch', '*launch.*'))),
        ('share/' + package_name + '/config', glob.glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='shosae',
    maintainer_email='phone13324@gmail.com',
    description='Standalone direct-camera ArUco marker pose publisher.',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'aruco_marker_pose_node=aruco_node.aruco_marker_pose_node:main',
        ],
    },
)
