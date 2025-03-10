# yolov3fromzero

依赖包:
```
albumentations
torch
numpy
cv2
```


使用前根据自己的代码的实际路径替换下面的`/home/autocore/work`
```
export PYTHONPATH=$PYTHONPATH:/home/autocore/work/yolov3fromzero:/home/autocore/work/yolov3fromzero/models
```

数据集存放于coco目录下.结构如下.
```
coco
├── images

│   ├── train2014
│   ├── train2017
│   ├── val2014
│   └── val2017
└── labels
    ├── train2014
    ├── train2017
    ├── val2014
    └── val2017
```

input_imgs目录用于存放原图经过处理后输入到模型的图片.
out_imgs目录用于存放在原始图片上的检测效果图.

```
cd yolov3fromzero
mkdir input_imgs
mkdir out_imgs
```

## 检测train.txt里是否有不存在label的图片
python coco/check_traintxt.py
如果有,修正traintxt. 新的文件命名为xxx.new
label的格式默认为yolo的格式. cxywh xywh为比例.

## 测试数据处理
```
python dataset/dataset.py
```
会生成经过数据处理后送进模型的输入图片,位于input_imgs目录.

## 训练
python train.py


# 数据增强库bug
https://github.com/albumentations-team/albumentations/issues/459#issuecomment-734454278

