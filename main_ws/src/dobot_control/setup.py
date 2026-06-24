from glob import glob
from setuptools import find_packages, setup

package_name = 'dobot_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ssafy',
    maintainer_email='ssafy@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'pixel_to_base = dobot_control.pixel_to_base:main',
            'grid_pnp_calibrator = dobot_control.grid_pnp_calibrator:main',
            'image_crop_viewer = dobot_control.image_crop_viewer:main',
            'click_pick_place = dobot_control.click_pick_place:main',
            'red_plate_command = dobot_control.red_plate_command:main',
            'red_plate_interactive_calibrator = '
            'dobot_control.red_plate_interactive_calibrator:main',
        ],
    },
)
