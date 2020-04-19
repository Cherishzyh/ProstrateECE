import os
import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tensorboardX import SummaryWriter
from pytorchtools import EarlyStopping

from T4T.Utility.Loader import BinaryOneImageOneLabel, BinaryOneImageOneLabelTest
from T4T.Utility.ImageProcessor import ImageProcess2D
# from T4T.Utility.Metric import AUC
from MeDIT.DataAugmentor import random_2d_augment

from Model.UNet import Unet
from FilePath import *


def BinaryPred(prediction):
    one = torch.ones_like(prediction)
    zero = torch.zeros_like(prediction)
    binary_prediction = torch.where(prediction > 0.5, one, zero)
    return binary_prediction

def Train():
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    processor = ImageProcess2D(reverse_channel=False, augment_param=random_2d_augment)

    data_shape = {'input_0': (1, 184, 184), 'output_0': (2,)}

    # writer = SummaryWriter(log_dir=graph_folder, comment='Net')

    train_set = BinaryOneImageOneLabel(root_folder=input_0_output_0_train,
                                     data_shape=data_shape,
                                     processor=processor)

    valid_set = BinaryOneImageOneLabel(root_folder=input_0_output_0_validation,
                                     data_shape=data_shape,
                                     processor=processor)

    train_loader = DataLoader(train_set, batch_size=12, shuffle=True)

    valid_loader = DataLoader(valid_set, batch_size=12, shuffle=True)

    model = Unet(in_channels=1, out_channels=1)
    model = model.to(device)

    lr = 0.001
    train_loss = 0.0
    valid_loss = 0.0
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=20, factor=0.5, verbose=True)
    early_stopping = EarlyStopping(patience=100, verbose=True)

    for epoch in range(150):
        train_loss_list, valid_loss_list= [], []
        train_auc_list, valid_auc_list = [], []
        model.train()

        for i, train_data in enumerate(train_loader):
            inputs, labels = train_data
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()

            outputs = model(inputs)

            loss = criterion(outputs, labels)
            # train_auc.append(metric_auc.__call__(outputs, labels))

            loss.backward()
            optimizer.step()

            # TODO:
            label_list.append(np.squeeze(labels.cpu().numpy())[0])
            pred_list.append(np.squeeze(outputs.cpu().detach().numpy())[0])
            train_auc = get_auc(pred_list, label_list)

            train_loss_list.append(loss.item())
            train_auc_list.append(train_auc)
            train_loss += loss.item()

        model.eval()
        for i, valid_data in enumerate(valid_loader):
            inputs, labels = valid_data
            inputs, labels = inputs.to(device), labels.to(device)

            outputs = model(inputs)

            loss = criterion(outputs, labels)

            valid_loss_list.append(loss.item())
            valid_loss += loss.item()

            # TODO:
            label_list.append(np.squeeze(labels.cpu().numpy())[0])
            pred_list.append(np.squeeze(outputs.cpu().detach().numpy())[0])
            valid_auc = get_auc(pred_list, label_list)
            valid_auc_list.append(valid_auc)

            if (i + 1) % 10 == 0:
                print('Epoch [%d / %d], Iter [%d], Train Loss: %.4f, Train auc: %.4f, Valid Loss: %.4f, valid auc: %.4f' %
                      (epoch + 1, 150, i + 1, train_loss/10, train_auc,  valid_loss/10, valid_auc))
                # print('Loss: %.4f, Auc: %.4f'.format(train_loss/10, np.mean(train_auc)))
                train_loss = 0.0
                valid_loss = 0.0

        scheduler.step(valid_loss)

        early_stopping(valid_loss, model)

        if early_stopping.early_stop:
            print("Early stopping")
            break

        # writer.add_scalars('Train_Val_Loss', {'train_loss_list': np.mean(train_loss_list), 'val_loss': np.mean(valid_loss_list)}, epoch+1)
        # writer.close()

        print('Epoch:', epoch + 1, 'Training Loss:', np.mean(train_loss_list), 'Valid Loss:', np.mean(valid_loss_list))

        state = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict()
        }
        torch.save(state, PATH)
    # torch.save(model, model_save_path)

def Test():
    from Metric.classification_statistics import get_auc, compute_confusion_matrix
    from sklearn import metrics

    total = 0.0
    correct = 0.0

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    data_shape = {'input_0': (1, 280, 280), 'output_0': (2,)}

    test_set = BinaryOneImageOneLabelTest(root_folder=test_folder, data_shape=data_shape)
    test_loader = DataLoader(test_set, batch_size=1, shuffle=True)

    # model = torch.load(model_path)
    model = Unet(in_channels=1, out_channels=1)
    checkpoint = torch.load(model_path)
    model.load_state_dict(checkpoint['net'])
    optimizer.load_state_dict(checkpoint['optimizer'])
    start_epoch = checkpoint['epoch'] + 1

    label_list = []
    pred_list = []
    binary_list = []
    for i, test_data in enumerate(test_loader):
        inputs, labels = test_data
        inputs, labels = inputs.to(device), labels.to(device)
        outputs = model(inputs)
        outputs = torch.sigmoid(outputs)
        binary_outputs = BinaryPred(outputs)
        label_list.append(np.squeeze(labels.cpu().numpy())[0])
        pred_list.append(np.squeeze(outputs.cpu().detach().numpy())[0])
        binary_list.append(np.squeeze(binary_outputs.cpu().detach().numpy())[0])

    auc = get_auc(pred_list, label_list)
    compute_confusion_matrix(binary_list, label_list, model_name='ECE-UNet')
    print(auc)
        # total += labels.size(0)

    # correct += (outputs == labels).sum()
    # print('Accuracy of the model on the test image: %d %%' % (100 * correct / total))


if __name__ == '__main__':
    # data_path = r'/home/zhangyihong/Documents/zhangyihong/Documents/ProstateECE/input_0_output_0/Train'
    # case_list = os.listdir(data_path)
    # print(case_list)
    Train()
    # Test()