from setuptools import setup

package_name = 'img_proc'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='orin@todo.todo',
    description='Kaşif Çelebi Image Processing',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'image_proc = img_proc.ImageProcc:main',
            'image_proc_label = img_proc.ImageProccLabels:main'
        ],
    },
)
