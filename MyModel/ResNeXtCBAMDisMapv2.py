from __future__ import division
import math
import torch.nn as nn
import torch.nn.functional as F
import torch

from MyModel.Block import conv1x1


'''
v1: all layers add distance map
v2: only layer1 and layer2 add distance map

'''


class ChannelAttention(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super(ChannelAttention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)

        self.fc1 = nn.Conv2d(in_planes, in_planes // ratio, 1, bias=False)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Conv2d(in_planes // ratio, in_planes, 1, bias=False)

        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = self.fc2(self.relu1(self.fc1(self.avg_pool(x))))
        max_out = self.fc2(self.relu1(self.fc1(self.max_pool(x))))
        out = avg_out + max_out

        return self.sigmoid(out)


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size=7):
        super(SpatialAttention, self).__init__()

        assert kernel_size in (3, 7), 'kernel size must be 3 or 7'
        padding = 3 if kernel_size == 7 else 1

        self.conv1 = nn.Conv2d(2, 1, kernel_size, padding=padding, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        x = torch.cat([avg_out, max_out], dim=1)
        x = self.conv1(x)

        return self.sigmoid(x)


class DisBottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, baseWidth=4, cardinality=32, stride=1, downsample=None, downstride=2):
        """ Constructor
        Args:
            inplanes: input channel dimensionality
            planes: output channel dimensionality
            baseWidth: base width.
            cardinality: num of convolution groups.
            stride: conv stride. Replaces pooling layer.
        """
        super(DisBottleneck, self).__init__()

        D = int(math.floor(planes * (baseWidth / 64)))
        C = cardinality

        self.conv1 = nn.Conv2d(inplanes, D*C, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn1 = nn.BatchNorm2d(D*C)
        self.conv2 = nn.Conv2d(D*C, D*C, kernel_size=3, stride=stride, padding=1, groups=C, bias=False)
        self.bn2 = nn.BatchNorm2d(D*C)
        self.conv3 = nn.Conv2d(D*C, planes * 4, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)

        self.ca = ChannelAttention(planes * 4)
        self.sa_fm = SpatialAttention()

        if downsample is True:
            self.downsample = nn.Sequential(
                conv1x1(inplanes, planes * self.expansion*2, downstride),
                nn.BatchNorm2d(planes * self.expansion*2),
            )
        else:
            self.downsample = None

    def forward(self, feature_map, dis_map):
        residual = feature_map

        out = self.conv1(feature_map)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        shape = out.shape[2:]
        dis_map_resize = F.interpolate(dis_map, size=shape, mode='bilinear')

        out = self.ca(out) * out
        out_fm = self.sa_fm(out) * out
        out_dm = dis_map_resize * out

        out = torch.cat([out_fm, out_dm], dim=1)

        if self.downsample is not None:
            residual = self.downsample(feature_map)

        out += residual
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, baseWidth=4, cardinality=32, stride=1, downsample=None, downstride=2):
        """ Constructor
        Args:
            inplanes: input channel dimensionality
            planes: output channel dimensionality
            baseWidth: base width.
            cardinality: num of convolution groups.
            stride: conv stride. Replaces pooling layer.
        """
        super(Bottleneck, self).__init__()

        D = int(math.floor(planes * (baseWidth / 64)))
        C = cardinality

        self.conv1 = nn.Conv2d(inplanes, D*C, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn1 = nn.BatchNorm2d(D*C)
        self.conv2 = nn.Conv2d(D*C, D*C, kernel_size=3, stride=stride, padding=1, groups=C, bias=False)
        self.bn2 = nn.BatchNorm2d(D*C)
        self.conv3 = nn.Conv2d(D*C, planes * 4, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * 4)
        self.relu = nn.ReLU(inplace=True)

        self.ca = ChannelAttention(planes * 4)
        self.sa = SpatialAttention()

        if downsample is True:
            self.downsample = nn.Sequential(
                conv1x1(inplanes, planes * self.expansion, downstride),
                nn.BatchNorm2d(planes * self.expansion),
            )
        else:
            self.downsample = None

    def forward(self, feature_map):
        residual = feature_map

        out = self.conv1(feature_map)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        out = self.ca(out) * out
        out = self.sa(out) * out

        if self.downsample is not None:
            residual = self.downsample(feature_map)

        out += residual
        out = self.relu(out)

        return out


class Layer1(nn.Module):
    def __init__(self, inplanes):
        super(Layer1, self).__init__()
        self.inplanes = inplanes
        self.layer1_0 = DisBottleneck(inplanes=self.inplanes, planes=self.inplanes, downsample=True, downstride=1)
        self.layer1_1 = DisBottleneck(inplanes=self.inplanes * 8, planes=self.inplanes)
        self.layer1_2 = DisBottleneck(inplanes=self.inplanes * 8, planes=self.inplanes)

    def forward(self, x, dis_map):
        x = self.layer1_0(x, dis_map)
        x = self.layer1_1(x, dis_map)
        x = self.layer1_2(x, dis_map)
        return x


class Layer2(nn.Module):
    def __init__(self, inplanes):
        self.inplanes = inplanes

        super(Layer2, self).__init__()
        self.layer2_0 = DisBottleneck(inplanes=self.inplanes * 8, planes=self.inplanes * 2, stride=2, downsample=True)
        self.layer2_1 = DisBottleneck(inplanes=self.inplanes * 16, planes=self.inplanes * 2)
        self.layer2_2 = DisBottleneck(inplanes=self.inplanes * 16, planes=self.inplanes * 2)
        self.layer2_3 = DisBottleneck(inplanes=self.inplanes * 16, planes=self.inplanes * 2)

    def forward(self, x, dis_map):
        x = self.layer2_0(x, dis_map)
        x = self.layer2_1(x, dis_map)
        x = self.layer2_2(x, dis_map)
        x = self.layer2_3(x, dis_map)

        return x


class Layer3(nn.Module):
    def __init__(self, inplanes):
        super(Layer3, self).__init__()
        self.inplanes = inplanes

        self.layer3_0 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2, stride=2, downsample=True)
        self.layer3_1 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2)
        self.layer3_2 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2)
        self.layer3_3 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2)
        self.layer3_4 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2)
        self.layer3_5 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes // 2)

    def forward(self, x):
        x = self.layer3_0(x)
        x = self.layer3_1(x)
        x = self.layer3_2(x)
        x = self.layer3_3(x)
        x = self.layer3_4(x)
        x = self.layer3_5(x)
        return x


class Layer4(nn.Module):
    def __init__(self, inplanes):
        super(Layer4, self).__init__()
        self.inplanes = inplanes

        self.layer4_0 = Bottleneck(inplanes=self.inplanes * 2, planes=self.inplanes, stride=2, downsample=True)
        self.layer4_1 = Bottleneck(inplanes=self.inplanes * 4, planes=self.inplanes)
        self.layer4_2 = Bottleneck(inplanes=self.inplanes * 4, planes=self.inplanes)

    def forward(self, x):
        x = self.layer4_0(x)
        x = self.layer4_1(x)
        x = self.layer4_2(x)

        return x


class ResNeXt(nn.Module):

    def __init__(self, in_channels, num_classes, baseWidth=4, cardinality=32):
        """ Constructor
        Args:
            baseWidth: baseWidth for ResNeXt.
            cardinality: number of convolution groups.
            layers: config of layers, e.g., [3, 4, 6, 3]
            num_classes: number of classes
        """
        super(ResNeXt, self).__init__()

        self.cardinality = cardinality
        self.baseWidth = baseWidth
        self.num_classes = num_classes
        self.inplanes = 32

        self.conv1 = nn.Conv2d(in_channels, self.inplanes, 3, 1, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(self.inplanes)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool1 = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        self.layer1 = Layer1(self.inplanes)
        self.layer2 = Layer2(self.inplanes)
        self.layer3 = Layer3(256)
        self.layer4 = Layer4(256)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc1 = nn.Linear(512 * 2, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def forward(self, inputs, dis_map):
        x = self.conv1(inputs)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool1(x)
        x = self.layer1(x, dis_map)
        x = self.layer2(x, dis_map)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        return x


if __name__ == '__main__':
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    model = ResNeXt(3, 1).to(device)
    print(model)
    inputs = torch.randn(1, 3, 192, 192).to(device)
    dis_map = torch.randn(1, 1, 192, 192).to(device)
    prediction = model(inputs, dis_map)