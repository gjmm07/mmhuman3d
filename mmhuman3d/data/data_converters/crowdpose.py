import json
import os

import numpy as np
from tqdm import tqdm

from mmhuman3d.core.conventions.keypoints_mapping import convert_kps
from .base_converter import BaseModeConverter
from .builder import DATA_CONVERTERS


@DATA_CONVERTERS.register_module()
class CrowdposeConverter(BaseModeConverter):

    ACCEPTED_MODES = ['val', 'train', 'trainval', 'test']

    def __init__(self, modes=[]):
        super(CrowdposeConverter, self).__init__(modes)

    def convert_by_mode(self, dataset_path, out_path, mode):
        # total dictionary to store all data
        total_dict = {}

        # structs we need
        image_path_, keypoints2d_, bbox_xywh_ = [], [], []

        # json annotation file
        json_path = os.path.join(dataset_path,
                                 'crowdpose_{}.json'.format(mode))

        json_data = json.load(open(json_path, 'r'))

        imgs = {}
        for img in json_data['images']:
            imgs[img['id']] = img

        for annot in tqdm(json_data['annotations']):

            # image name
            image_id = annot['image_id']
            img_path = str(imgs[image_id]['file_name'])
            img_path = os.path.join('images', img_path)

            # scale and center
            bbox_xywh = np.array(annot['bbox'])

            # keypoints processing
            keypoints2d = np.array(annot['keypoints'])
            keypoints2d = np.reshape(keypoints2d, (14, 3))
            keypoints2d[keypoints2d[:, 2] > 0, 2] = 1
            # check if all keypoints are annotated
            if sum(keypoints2d[:, 2] > 0) < 14:
                continue

            # check that all joints are within image bounds
            height = imgs[image_id]['height']
            width = imgs[image_id]['width']
            x_in = np.logical_and(keypoints2d[:, 0] < width,
                                  keypoints2d[:, 0] >= 0)
            y_in = np.logical_and(keypoints2d[:, 1] < height,
                                  keypoints2d[:, 1] >= 0)
            ok_pts = np.logical_and(x_in, y_in)
            if np.sum(ok_pts) < 14:
                continue

            # store data
            image_path_.append(img_path)
            keypoints2d_.append(keypoints2d)
            bbox_xywh_.append(bbox_xywh)

        # convert keypoints
        keypoints2d_ = np.array(keypoints2d_).reshape((-1, 14, 3))
        keypoints2d_, mask = convert_kps(keypoints2d_, 'crowdpose',
                                         'human_data')

        total_dict['image_path'] = image_path_
        total_dict['keypoints2d'] = keypoints2d_
        total_dict['bbox_xywh'] = bbox_xywh_
        total_dict['mask'] = mask
        total_dict['config'] = 'crowdpose'

        # store the data struct
        if not os.path.isdir(out_path):
            os.makedirs(out_path)
        out_file = os.path.join(out_path, 'crowdpose_{}.npz'.format(mode))
        np.savez_compressed(out_file, **total_dict)