# Copyright (c) 2015-present, Facebook, Inc.
# All rights reserved.
import os
import json

from torchvision import datasets, transforms
from torchvision.datasets.folder import ImageFolder, default_loader

from timm.data.constants import IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD
from timm.data import create_transform
from mcloader import ClassificationDataset, FashionGenDatasetPreTrain, FashionGenDatasetDownstream_Retrieval, FashionGenDatasetDownstream_Recognition


class INatDataset(ImageFolder):
    def __init__(self, root, train=True, year=2018, transform=None, target_transform=None,
                 category='name', loader=default_loader):
        self.transform = transform
        self.loader = loader
        self.target_transform = target_transform
        self.year = year
        # assert category in ['kingdom','phylum','class','order','supercategory','family','genus','name']
        path_json = os.path.join(root, f'{"train" if train else "val"}{year}.json')
        with open(path_json) as json_file:
            data = json.load(json_file)

        with open(os.path.join(root, 'categories.json')) as json_file:
            data_catg = json.load(json_file)

        path_json_for_targeter = os.path.join(root, f"train{year}.json")

        with open(path_json_for_targeter) as json_file:
            data_for_targeter = json.load(json_file)

        targeter = {}
        indexer = 0
        for elem in data_for_targeter['annotations']:
            king = []
            king.append(data_catg[int(elem['category_id'])][category])
            if king[0] not in targeter.keys():
                targeter[king[0]] = indexer
                indexer += 1
        self.nb_classes = len(targeter)

        self.samples = []
        for elem in data['images']:
            cut = elem['file_name'].split('/')
            target_current = int(cut[2])
            path_current = os.path.join(root, cut[0], cut[2], cut[3])

            categors = data_catg[target_current]
            target_current_true = targeter[categors[category]]
            self.samples.append((path_current, target_current_true))

    # __getitem__ and __len__ inherited from ImageFolder


def build_dataset(is_train, args):
    transform = build_transform(is_train, args)

    if args.data_set == 'CIFAR':
        dataset = datasets.CIFAR100(args.data_path, train=is_train, transform=transform)
        nb_classes = 100
        return dataset, nb_classes
        
    elif args.data_set == 'IMNET':
        if not args.use_mcloader:
            root = os.path.join(args.data_path, 'train' if is_train else 'val')
            dataset = datasets.ImageFolder(root, transform=transform)
        else:
            dataset = ClassificationDataset(
                'train' if is_train else 'val',
                pipeline=transform
            )
        nb_classes = 1000
        return dataset, nb_classes

    elif args.data_set == "IMNET-TINY100":
        if not args.use_mcloader:
            root = os.path.join(args.data_path, 'train' if is_train else 'val')
            dataset = datasets.ImageFolder(root, transform=transform)
        else:
            dataset = ClassificationDataset(
                'train' if is_train else 'val',
                pipeline=transform
            )
        nb_classes = 100
        return dataset, nb_classes

    elif args.data_set == 'INAT':
        dataset = INatDataset(args.data_path, train=is_train, year=2018,
                              category=args.inat_category, transform=transform)
        nb_classes = dataset.nb_classes
        return dataset, nb_classes

    elif args.data_set == 'INAT19':
        dataset = INatDataset(args.data_path, train=is_train, year=2019,
                              category=args.inat_category, transform=transform)
        nb_classes = dataset.nb_classes
        return dataset, nb_classes

    elif args.data_set == 'FashionGen':
        if args.eval_retrieval_tir or args.eval_retrieval_itr:
            print('>>> load FashionGenDatasetDownstream_Retrieval at `./datasets.py`')
            dataset = FashionGenDatasetDownstream_Retrieval(
                root=args.data_path, 
                args=args
                )
        elif args.eval_recognition:
            print('>>> load FashionGenDatasetDownstream_Recognition at `./datasets.py`')
            dataset = FashionGenDatasetDownstream_Recognition(
                root=args.data_path, 
                args=args
                )
        else:
            print('>>> load FashionGenDatasetPreTrain at `./datasets.py`')
            dataset = FashionGenDatasetPreTrain(
                root=args.data_path, 
                # trainsize=args.input_size, 
                data_type='train' if is_train else 'valid', 
                # max_token_length=args.num_text_tokens, 
                # word_mask_rate=args.word_mask_rate, 
                is_train=True if is_train else False,
                # if_itm=True if args.loss_type['itm'] == 1 else False,
                # if_itg=True if args.loss_type['itg'] == 1 else False,
                # mask_ratio=args.mask_ratio,
                # mask_strategy=args.mask_strategy,
                args=args
                )
        return dataset
    else:
        raise ValueError('Unknown dataset: {}'.format(args.data_set))
    


def build_transform(is_train, args):
    resize_im = args.input_size > 32
    if is_train:
        # this should always dispatch to transforms_imagenet_train
        transform = create_transform(
            input_size=args.input_size,
            is_training=True,
            color_jitter=args.color_jitter,
            auto_augment=args.aa,
            interpolation=args.train_interpolation,
            re_prob=args.reprob,
            re_mode=args.remode,
            re_count=args.recount,
        )
        if not resize_im:
            # replace RandomResizedCropAndInterpolation with
            # RandomCrop
            transform.transforms[0] = transforms.RandomCrop(
                args.input_size, padding=4)
        return transform

    t = []
    if resize_im:
        size = int((256 / 224) * args.input_size)
        t.append(
            transforms.Resize(size, interpolation=3),  # to maintain same ratio w.r.t. 224 images
        )
        t.append(transforms.CenterCrop(args.input_size))

    t.append(transforms.ToTensor())
    t.append(transforms.Normalize(IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD))
    return transforms.Compose(t)
