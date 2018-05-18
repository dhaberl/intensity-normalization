#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
intensity_normalize.utilities.register

handles required registration for intensity normalization routines

Author: Jacob Reinhold (jacob.reinhold@jhu.edu)
Created on: May 08, 2018
"""

from glob import glob
import logging
import os

import ants
import numpy as np

from intensity_normalization.utilities.io import split_filename

logger = logging.getLogger(__name__)


def register_to_template(img_dir, out_dir=None, tx_dir=None, template_img=0):
    """
    register a set of images using SyN (deformable registration)
    and write their output and transformations to disk

    Args:
        img_dir (str): directory containing MR images registered to a template
        out_dir (str): directory to save images if you do not want them saved in
            a newly created directory (or existing dir) called `normalize_reg`
        tx_dir (str): directory to save registration tforms if you do not want them saved in
            a newly created directory (or existing dir) called `normalize_reg_tforms`
        template_img (int or str): number of img in img_dir, or a specified img path
            to be used as the template which all images are registered to

    Returns:
        None, writes registration transforms and registered images to disk
    """

    img_fns = sorted(glob(os.path.join(img_dir, '*.nii*')))
    logger.debug('Input images: {}'.format(img_fns))

    if isinstance(template_img, int):
        template_img = img_fns[template_img]

    if tx_dir is None:
        tx_dir = os.path.join(os.getcwd(), 'reg_tforms')
        if os.path.exists(tx_dir):
            logger.warning('normalize_reg_tforms directory already exists, '
                           'may overwrite existing tforms!')
        else:
            os.mkdir(tx_dir)

    if out_dir is None:
        out_dir = os.path.join(os.getcwd(), 'registered')
        if os.path.exists(out_dir):
            logger.warning('normalize_reg directory already exists, '
                           'may overwrite existing registered images!')
        else:
            os.mkdir(out_dir)

    img_fns = [fn for fn in img_fns if fn != template_img]
    template = ants.image_read(template_img)

    _, base, _ = split_filename(template_img)
    logger.debug('Template image: {}'.format(base))
    for i, fn in enumerate(img_fns, 1):
        _, base, _ = split_filename(fn)
        logger.debug('Image to register ({}): {}'.format(i, base))

    for i, fn in enumerate(img_fns, 1):
        img = ants.image_read(fn)
        _, base, _ = split_filename(fn)
        logger.info('Registering image {} out of {} (image name: {})'.format(i, len(img_fns), base))
        reg_result = ants.registration(template, img, type_of_transform='SyN')
        for j, tx_fn in enumerate(reg_result['invtransforms']):
            # transforms are actually saved as temp files, so need to load and resave them
            # and test that they are loadable!
            if j == 0:
                tx = ants.image_read(tx_fn)
                out_tx = os.path.join(tx_dir, base + '_deformable_tx.nii.gz')
                logger.debug('Output transform: {}'.format(out_tx))
                ants.image_write(tx, out_tx)
            else:
                tx = ants.read_transform(tx_fn)
                out_tx = os.path.join(tx_dir, base + '_affine_tx.mat')
                logger.debug('Output transform: {}'.format(out_tx))
                ants.write_transform(tx, out_tx)
        moved = reg_result['warpedmovout']
        moved_fn = os.path.join(out_dir, base + '_reg.nii.gz')
        logger.debug('Output registered image: {}'.format(moved_fn))
        ants.image_write(moved, moved_fn)
        del img, reg_result, tx, moved  # trying to prevent segfault


def unregister(reg_dir, tx_dir, template_img, out_dir=None):
    """
    undo the template registration process, this should be used with HM and RAVEL
    intensity normalization methods since they require the images to initially be
    deformably aligned

    Args:
        reg_dir (str): directory of registered (and normalized probably) nifti images
        tx_dir (str): directory to from which to load registration tforms
        out_dir (str): directory to save de-registered images if you do not want them saved in
            a newly created directory (or existing dir) called `normalized`
        template_img (int or str): a specified img path used as the template which all
            images were registered to

    Returns:
        None, writes de-registered images to disk
    """
    reg_fns = sorted(glob(os.path.join(reg_dir, '*.nii*')))
    affine_fns = sorted(glob(os.path.join(tx_dir, '*.mat')))
    deformable_fns = sorted(glob(os.path.join(tx_dir, '*.nii.gz')))
    template = ants.image_read(template_img)
    if out_dir is None:
        out_dir = os.path.join(os.getcwd(), 'normalized')
        if os.path.exists(out_dir):
            logger.warning('normalized directory already exists, '
                           'may overwrite existing registered images!')
        else:
            os.mkdir(out_dir)

    for i, (fn, aff_fn, def_fn) in enumerate(zip(reg_fns, affine_fns, deformable_fns)):
        _, base, _ = split_filename(fn)
        img = ants.image_read(fn)
        transformlist = [def_fn, aff_fn]
        logger.info('De-registering image {} out of {}'.format(i, len(reg_fns)))
        unmoved = ants.apply_transforms(fixed=template, moving=img, interpolator='bSpline',
                                        transformlist=transformlist)
        ants.image_write(unmoved,os.path.join(out_dir, base + '_norm.nii.gz'))
        del img
