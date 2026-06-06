#!/usr/bin/env python3

from pathlib import Path
import time

import cv2
import depthai as dai
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage


class OakCameraNode(Node):
    def __init__(self):
        super().__init__('oak_person_detector_node')

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        
        self.image_pub = self.create_publisher(
            CompressedImage,
            '/oak/rgb/image_processed/compressed',
            qos
        )

        self.nnPath = str(Path.home() / "kasif_celebi_ws/models/yolov8n_coco_640x352.blob")
        if not Path(self.nnPath).exists():
            raise FileNotFoundError(f"Blob file not found: {self.nnPath}")

        self.syncNN = False

        self.pipeline = self.create_pipeline()
        self.device = dai.Device(self.pipeline)

        self.qRgb = self.device.getOutputQueue(
            name="rgb",
            maxSize=1,
            blocking=False
        )

        self.qDet = self.device.getOutputQueue(
            name="nn",
            maxSize=1,
            blocking=False
        )

        self.detections = []
        self.startTime = time.monotonic()
        self.counter = 0

        self.timer = self.create_timer(0.1, self.process_frame)

        self.get_logger().info("OAK person detector node started")

    def create_pipeline(self):
        pipeline = dai.Pipeline()

        camRgb = pipeline.create(dai.node.ColorCamera)
        detectionNetwork = pipeline.create(dai.node.YoloDetectionNetwork)
        xoutRgb = pipeline.create(dai.node.XLinkOut)
        nnOut = pipeline.create(dai.node.XLinkOut)

        xoutRgb.setStreamName("rgb")
        nnOut.setStreamName("nn")

        camRgb.setPreviewSize(640, 352)
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        camRgb.setInterleaved(False)
        camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        camRgb.setFps(10)

        detectionNetwork.setConfidenceThreshold(0.5)
        detectionNetwork.setNumClasses(80)
        detectionNetwork.setCoordinateSize(4)
        detectionNetwork.setIouThreshold(0.5)
        detectionNetwork.setBlobPath(self.nnPath)
        detectionNetwork.setNumInferenceThreads(2)
        detectionNetwork.input.setBlocking(False)

        camRgb.preview.link(detectionNetwork.input)

        if self.syncNN:
            detectionNetwork.passthrough.link(xoutRgb.input)
        else:
            camRgb.preview.link(xoutRgb.input)

        detectionNetwork.out.link(nnOut.input)

        return pipeline

    def frameNorm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def draw_detections(self, frame):
        color = (255, 0, 0)

        for detection in self.detections:
            if detection.label != 0:
                continue

            bbox = self.frameNorm(
                frame,
                (detection.xmin, detection.ymin, detection.xmax, detection.ymax)
            )

            cv2.putText(
                frame,
                "person",
                (bbox[0] + 10, bbox[1] + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

            cv2.putText(
                frame,
                f"{int(detection.confidence * 100)}%",
                (bbox[0] + 10, bbox[1] + 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )

            cv2.rectangle(
                frame,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                color,
                2
            )

        fps = self.counter / max((time.monotonic() - self.startTime), 1e-6)

        cv2.putText(
            frame,
            f"NN fps: {fps:.2f}",
            (2, frame.shape[0] - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1
        )

    def process_frame(self):
        try:
            inRgb = self.qRgb.tryGet()
            inDet = self.qDet.tryGet()

            if inDet is not None:
                self.detections = inDet.detections
                self.counter += 1

            if inRgb is None:
                return

            frame = inRgb.getCvFrame()
            output = frame.copy()

            if self.detections:
                self.draw_detections(output)

            success, encoded_image = cv2.imencode(
                '.jpg',
                output,
                [int(cv2.IMWRITE_JPEG_QUALITY), 60]
            )

            if not success:
                return

            msg = CompressedImage()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'camera_frame'
            msg.format = 'jpeg'
            msg.data = encoded_image.tobytes()

            self.image_pub.publish(msg)

        except Exception as e:
            self.get_logger().error(f"Processing error: {e}")

    def destroy_node(self):
        try:
            self.device.close()
        except Exception:
            pass

        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = OakCameraNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()