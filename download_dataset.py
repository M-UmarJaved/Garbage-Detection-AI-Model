from roboflow import Roboflow
rf = Roboflow(api_key="qG8XoU2Nx9nAWNEo4tfX")
project = rf.workspace("bear-logic-s-workspace").project("garbage-detection-n7huv")
dataset = project.version(1).download("yolov5")