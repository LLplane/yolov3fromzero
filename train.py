from models.models import *
from datasets.dataset import *
from utils.loss import *
from utils.utils import *
import time
import argparse
import test

parser = argparse.ArgumentParser()
parser.add_argument('-epochs', type=int, default=0, help='number of epochs')
parser.add_argument('-resume', default=False, help='resume training flag')
parser.add_argument('-batchsize', type=int,default=48, help='training batch size')
parser.add_argument('-cfg', type=str,default='cfg/yolov3.cfg', help='training cfg')
parser.add_argument('-traintxt', type=str,default='coco/train2017.txt', help='training txt')
parser.add_argument('-testtxt', type=str,default='coco/val2017.txt', help='testing txt')
parser.add_argument('-model_input_size', type=int,default=416, help='model_input_size')
parser.add_argument('-conf_thre', type=float,default=0.7, help='confidence threshold')
parser.add_argument('-iou_thre', type=float,default=0.5, help='iou threshold')
parser.add_argument('-cls_thre', type=float,default=0.7, help='class threshold')
parser.add_argument('-conf_loss_weights', type=int,default=2, help='conf loss weights')
parser.add_argument('-negconf_loss_weights', type=int,default=2, help='neg conf loss weights')
parser.add_argument('-cls_loss_weights', type=int,default=5, help='cls loss weights')
parser.add_argument('-cls_names_path', type=str,default='coco/names', help='class names file')
opt = parser.parse_args()
print(opt)
cls_names = load_classes(opt.cls_names_path)

if __name__ == '__main__':
    # Dataset
    # traintxt = '/home/autocore/work/yolov3_darknet/data/lishui/train.txt'
    root_dir=os.getcwd()
    traintxt = root_dir + '/' + opt.traintxt
    dataset = LoadImagesAndLabels(traintxt,imgsize=opt.model_input_size,aug=True,mosaic=True)
    dataloader = torch.utils.data.DataLoader(dataset,
                                            batch_size=opt.batchsize,
                                            num_workers=4,
                                            shuffle=True,
                                            collate_fn=dataset.collate_fn)
    cuda = torch.cuda.is_available()
    device = torch.device('cuda:0' if cuda else 'cpu')
    yolov3net = Yolov3(opt.cfg)
    yolov3net = yolov3net.to(device)
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, yolov3net.parameters()), lr=1e-4, weight_decay=5e-4)
    # optimizer = torch.optim.SGD(yolov3net.parameters(), lr=.001, momentum=.9, weight_decay=0.0005 * 0, nesterov=True)
    start_epoch = 0
    resume = opt.resume
    if resume:
        checkpoint_name = 'checkpoints/epoch{}.pt'.format(opt.epochs)
        checkpoint = torch.load(checkpoint_name)
        yolov3net.load_state_dict(checkpoint['model'])
        optimizer = torch.optim.Adam(yolov3net.parameters())
        optimizer.load_state_dict(checkpoint['optimizer'])
        start_epoch = checkpoint['epoch'] + 1
        print('resume done from {}*********************'.format(checkpoint_name))  
    
    yolov3net.train()
    loss = YoloLoss(yolov3net)

    mAP,best_mAP = 0.,0.
    now=datetime.datetime.now()
    log_name = './train_log_{}.txt'.format(now)
    f_log = open(log_name,'a+') 
    f_log.writelines('begin training********************')
    for epoch in range(start_epoch,100000): 
        print('epoch {}'.format(epoch))
        t0 = time.time()
        for i,data in enumerate(dataloader):
            imgs,labels,_ = data
            imgs = imgs.to(device)
            imgs = imgs.float()/255.
            # print(imgs.shape,labels.shape)
            # print(labels[:,0])
            yolo_out = yolov3net(imgs)
            # print([out.shape for out in yolo_out])

            lconf,lx,ly,lw,lh,lcls,pt_conf,nt_conf = loss.compute_loss(yolo_out,labels,neg_weight=5)
            total_loss = opt.conf_loss_weights * lconf + 2 * lx + 2 * ly + 0.1 * lw + 0.1 * lh + opt.cls_loss_weights * lcls
            # print('lconf={},lx={},ly={},lw={},lh={},lcls={}'.format(lconf.item(),lx.item(),ly.item(),lw.item(),lh.item(),lcls.item()))
            print('img:{},total_loss={},lconf:{},pt_conf:{},nt_conf:{}'.format(
                (1+i)*opt.batchsize,total_loss.item(),lconf.item(),pt_conf.item(),nt_conf.item()))
            optimizer.zero_grad() #清空梯度
            total_loss.backward() #反向传播
            optimizer.step()      #更新参数
        
        t1 = time.time()
        print('epoch{} train for {}'.format(epoch,(t1-t0)))

        checkpoint = {'epoch':epoch,
                      'model':yolov3net.state_dict(),
                      'optimizer':optimizer.state_dict()}
        if epoch % 1 == 0:
            checkpoint_name = 'checkpoints/epoch{}.pt'.format(epoch)
            torch.save(checkpoint,checkpoint_name)
        
        #写日志
        now=datetime.datetime.now()
        f_log.writelines('{},epoch:{},total_loss:{},pt_conf:{},nt_conf:{},lw={},lh={},lcls={}\n'. \
                format(str(now),epoch,total_loss.item(),pt_conf.item(),nt_conf.item(),lw.item(),lh.item(),lcls.item()))
        f_log.flush()

        #测试
        if epoch % 2 == 0:
            mAP = test.test(opt.cfg,opt.testtxt,checkpoint_name,opt.model_input_size,
                      opt.conf_thre,opt.iou_thre,opt.cls_thre,cls_names)

            if mAP > best_mAP:
                print('************************mAP:{},best_mAP:{}'.format(mAP,best_mAP))
                best_mAP = mAP

            f_log.writelines('epoch:{},mAP={},best_mAP={}\n'.format(epoch,mAP,best_mAP))
            f_log.flush()

        # if lconf.item() < 0.01 or total_loss.item() < 0.1 or mAP > 0.4:
        if mAP > 0.4:
            break
    f_log.close()

    torch.cuda.empty_cache()