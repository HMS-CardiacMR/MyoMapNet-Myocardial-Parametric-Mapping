'''
Created on May 21, 2018

@author: helrewaidy
'''
# sub-parts of the U-Net model

import torch

import torch.nn as nn
import torch.nn.functional as F


class double_conv(nn.Module):
    '''(conv => ReLU => BN) * 2'''
    def __init__(self, in_ch, out_ch):
        super(double_conv, self).__init__()
        self.conv = nn.Sequential(
                    nn.Conv2d(in_ch, out_ch, 3, padding=1),
                    # nn.BatchNorm2d(out_ch, affine=True), #, affine=False
                    nn.ReLU(inplace=True),
                    nn.Conv2d(out_ch, out_ch, 3, padding=1),
                    # nn.BatchNorm2d(out_ch, affine=True), #, affine=False
                    nn.ReLU(inplace=True)
                )

    def forward(self, x):
        x = self.conv(x)
        return x

class down_conv(nn.Module):
    def __init__(self, in_ch):
        super(down_conv, self).__init__()
        self.conv = nn.Sequential(
                    nn.Conv2d(in_ch, in_ch, [3,3],stride=(2,2), padding=1),
                    nn.BatchNorm2d(in_ch, affine=True), #, affine=False
                    nn.ReLU(inplace=True),
                    )

    def forward(self, x):
        x = self.conv(x)
        return x

class inconv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(inconv, self).__init__()
        self.conv = double_conv(in_ch, out_ch)

    def forward(self, x):
        x = self.conv(x)
        return x

class down(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(down, self).__init__()
        self.down_conv = down_conv(in_ch)
        self.double_conv = double_conv(in_ch, out_ch)

    def forward(self, x):
        down_x = self.down_conv(x)
        x = self.double_conv(down_x)
        return x, down_x 

class bottleneck(nn.Module):
    def __init__(self, in_ch, out_ch, residual_connection=True):
        super(bottleneck, self).__init__()
        self.residual_connection = residual_connection
        self.down_conv = down_conv(in_ch)
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_ch, 2*in_ch, 3, padding=1),
            nn.BatchNorm2d(2*in_ch, affine=True), #, affine=False
            nn.ReLU(inplace=True),
            
            nn.Conv2d(2*in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch, affine=True), #, affine=False
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        down_x = self.down_conv(x)
        if self.residual_connection:
            x = self.double_conv(down_x) + down_x
        else:
            x = self.double_conv(down_x)
            
        return x

class up(nn.Module):
    def __init__(self, in_ch, out_ch, bilinear=True):
        super(up, self).__init__()
        #  would be a nice idea if the upsampling could be learned too,
        #  but my machine do not have enough memory to handle all those weights
        if bilinear:
            self.up = nn.UpsamplingBilinear2d(scale_factor=2)
#             self.up = nn.Upsample(scale_factor=2, mode='bilinear')
        else:
            self.up = ComplexConvTranspose2d(in_ch, in_ch, (2,2), stride=(2,2))

        self.conv = nn.Sequential(
                    nn.Conv2d(in_ch * 2, in_ch, 3, padding=1),
                    nn.BatchNorm2d(in_ch, affine=True), #, affine=False
                    nn.ReLU(inplace=True),

                    nn.Conv2d(in_ch , out_ch, 3, padding=1),
                    nn.BatchNorm2d(out_ch, affine=True), #, affine=False
                    nn.ReLU(inplace=True)
                )

    def forward(self, x1, x2):
        x1 = self.up(x1)
        diffX = x1.size()[2] - x2.size()[2]
        diffY = x1.size()[3] - x2.size()[3]
        x2 = F.pad(x2, (diffX // 2, int(diffX / 2),
                        diffY // 2, int(diffY / 2)))
        x = torch.cat([x2, x1], dim=1)
        x = self.conv(x)
        return x
    
class mag_phase_combine(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(mag_phase_combine, self).__init__()
        self.conv1d = nn.Sequential(
            # HOSSAM :: Please Remove the patch Normalization from here if it didn't work
#             nn.BatchNorm2d(in_ch),
            ComplexConv2d(in_ch, out_ch, [1, 1], padding=(0,0))
        )

    def forward(self, x):
        t = torch.split(x, int(x.size()[2]/2), dim=2)
        xt = [i for i in t]
        x1 = xt[0]
        x2 = xt[1]
        x = torch.cat([x1, x2], dim=1)
        x = self.conv1d(x)
        return x

class outconv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super(outconv, self).__init__()
        self.conv = nn.Conv2d(in_ch, out_ch, [1, 1])

    def forward(self, x):
        x = self.conv(x)
        return x
