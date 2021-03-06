'''
if dwi_2000 exist dwi_2000
elif dwi 取最大的
elif dki 取最大的
'''


import os
import shutil
import numpy as np
import nibabel as nib
import SimpleITK as sitk

from MeDIT.SaveAndLoad import LoadNiiData
from MeDIT.Visualization import Imshow3DArray
from MeDIT.Normalize import Normalize01

# from FilePath import process_folder, resample_folder, desktop_path


def NearTrueB(b_list):
    dis = []
    for index in b_list:
        dis.append(abs(float(index) - 1500))
    index = dis.index(min(dis))
    return b_list[index], index

def MoveFile():
    pass


def GetDWIPath(case):
    print(case)
    if case == 'WYB^wu yi bao' or case == 'ZYB^zhang yun bao':
        return 0

    b_value = ['0', '50', '700', '750', '1400', '1500']
    case_path = os.path.join(process_folder, case)

    if os.path.exists(os.path.join(case_path, 'adc.nii')):
        if os.path.exists(os.path.join(case_path, 'dwi.nii')):
            bval_path = os.path.join(case_path, 'dwi.bval')
            bval = open(bval_path, 'r')
            b_list = bval.read().split()
            if len(b_list) == 1:
                new_img, new_dwi, _ = LoadNiiData(os.path.join(case_path, 'dwi.nii'))

            else:
                b, index = NearTrueB(b_list)
                _, dwi, _ = LoadNiiData(os.path.join(case_path, 'dwi.nii'))
                img, _, _ = LoadNiiData(os.path.join(case_path, 'adc.nii'))
                new_dwi = dwi[index, ...]
                new_img = sitk.GetImageFromArray(new_dwi)
                new_img.SetDirection(img.GetDirection())
                new_img.SetSpacing(img.GetSpacing())
                new_img.SetOrigin(img.GetOrigin())

        elif os.path.exists(os.path.join(case_path, 'dki.nii')):
            bval_path = os.path.join(case_path, 'dki.bval')
            bval = open(bval_path, 'r')
            b_list = bval.read().split()
            if len(b_list) == 1:
                new_img, new_dwi, _ = LoadNiiData(os.path.join(case_path, 'dki.nii'))
            else:
                b, index = NearTrueB(b_list)
                img, dki, _ = LoadNiiData(os.path.join(case_path, 'dki.nii'))
                img, _, _ = LoadNiiData(os.path.join(case_path, 'adc.nii'))
                new_dwi = dki[index, ...]
                new_img = sitk.GetImageFromArray(new_dwi)
                new_img.SetDirection(img.GetDirection())
                new_img.SetSpacing(img.GetSpacing())
                new_img.SetOrigin(img.GetOrigin())

        else:
            for b in reversed(b_value):
                if os.path.exists(os.path.join(case_path, 'dwi_b'+str(b)+'.nii')):
                    new_img, new_dwi, _ = LoadNiiData(os.path.join(case_path, 'dwi_b'+str(b)+'.nii'))
                    break
    try:
        sitk.WriteImage(new_img, os.path.join(case_path, 'max_b_dwi.nii'))
        # print('Image size is: ', new_img.GetSize())
        # print('Image resolution is: ', new_img.GetSpacing())
        # print('Image direction is: ', new_img.GetDirection())
        # print('Image Origion is: ', new_img.GetOrigin())
    except Exception as e:
        print(case, e)

def test():

    case_list = os.listdir(process_folder)
    for case in case_list:
        GetDWIPath(case)

    # try:
    #     path = os.path.join(desktop_path, case + 'max_b.nii')
    #     _, data, _ = LoadNiiData(path)
    #     data = np.transpose(data, (1, 2, 0))
    #     Imshow3DArray(Normalize01(data))
    # except Exception as e:
    #     print(case)

def xxx():
    case_list = os.listdir(process_folder)
    for case in case_list:
        if case == 'WYB^wu yi bao' or case == 'ZYB^zhang yun bao':
            continue
        case_path = os.path.join(process_folder, case)

        if os.path.exists(os.path.join(case_path, 'dwi.nii')):
            bval_path = os.path.join(case_path, 'dwi.bval')
            bval = open(bval_path, 'r')
            b_list = bval.read().split()
            if len(b_list) == 1:
                print(case)

        elif os.path.exists(os.path.join(case_path, 'dki.nii')):
            bval_path = os.path.join(case_path, 'dki.bval')
            bval = open(bval_path, 'r')
            b_list = bval.read().split()
            if len(b_list) == 1:
                print(case)

def SelectBinTest():
    test_folder = r'X:\CNNFormatData\ProstateCancerECE\NPYNoDivide\Test\DwiSlice'
    des_folder = r'X:\CNNFormatData\ProstateCancerECE\NPYNoDivide\Test\DWISliceb1500'
    b_folder = r'X:\PrcoessedData\ProstateCancerECE'
    b_value = ['0', '50', '700', '750', '1400', '1500']
    for num, case in enumerate(os.listdir(test_folder)):

        case_name = case[:case.index('_slice')]
        case_path = os.path.join(test_folder, case)
        des_path = os.path.join(des_folder, case)

        # if os.path.exists(os.path.join(b_folder, case_name + '/dwi.bval')):
        #     bval_path = os.path.join(b_folder,  case_name + '/dwi.bval')
        #     b_list = open(bval_path, 'r').read().split()
        #     b, index = NearTrueB(b_list)
        #
        #     if float(b) >= 1000:
        #         shutil.copy(case_path, des_path)
        #         print('number:{}, {} b is {}, copy sucessfully!'.format(num, case_name, b))
        #         pass
        #     else:
        #         print('number:{}, {} b is {}, do not copy.'.format(num, case_name, b))
        #
        # elif os.path.exists(os.path.join(b_folder, case_name + '/dki.bval')):
        #     bval_path = os.path.join(b_folder,  case_name + '/dki.bval')
        #     b_list = open(bval_path, 'r').read().split()
        #     b, index = NearTrueB(b_list)
        #
        #     if float(b) >= 1000:
        #         shutil.copy(case_path, des_path)
        #         print('number:{}, {} b is {}, copy sucessfully!'.format(num, case_name, b))
        #         pass
        #     else:
        #         print('number:{}, {} b is {}, do not copy.'.format(num, case_name, b))
        #
        # else:
        #     for b in reversed(b_value):
        #         if os.path.exists(os.path.join(b_folder, case_name + '/dwi_b' + str(b) + '.nii')) \
        #                 or os.path.exists(os.path.join(b_folder, case_name + '/dki_b' + str(b) + '.nii')):
        #             if float(b) >= 1000:
        #                 shutil.copy(case_path, des_path)
        #                 print('number:{}, {} b is {}, copy sucessfully!'.format(num, case_name, b))
        #                 break
        #             else:
        #                 print('number:{}, {} b is {}, do not copy.'.format(num, case_name, b))



        if os.path.exists(os.path.join(b_folder, case_name + '/dwi.bval')):
            bval_path = os.path.join(b_folder,  case_name + '/dwi.bval')
            b_list = open(bval_path, 'r').read().split()
            b, index = NearTrueB(b_list)
            if float(b) < 1000:
                # pass
                print(case_name)
                print('b is {}.'.format(b))

        elif os.path.exists(os.path.join(b_folder, case_name + '/dki.bval')):
            bval_path = os.path.join(b_folder,  case_name + '/dki.bval')
            b_list = open(bval_path, 'r').read().split()
            b, index = NearTrueB(b_list)
            if float(b) < 1000:
                # pass
                print(case_name)
                print('b is {}..'.format(b))

        else:
            # print(case_name)
            for b in reversed(b_value):
                if os.path.exists(os.path.join(b_folder, case_name + '/dwi_b' + str(b) + '.nii')) \
                        or os.path.exists(os.path.join(b_folder, case_name + '/dki_b' + str(b) + '.nii')):
                    if float(b) < 1000:
                        print(case_name)
                        print('b is {}...'.format(b))
                        break

if __name__ == '__main__':
    SelectBinTest()









