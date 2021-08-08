# -*- coding: utf-8 -*-
"""
intensity_normalization.normalize.lsq

Author: Jacob Reinhold (jcreinhold@gmail.com)
Created on: Jun 01, 2021
"""

__all__ = [
    "LeastSquaresNormalize",
]

from typing import List, Optional

import numpy as np

from intensity_normalization.type import Array, Vector
from intensity_normalization.normalize.base import NormalizeFitBase
from intensity_normalization.util.tissue_membership import find_tissue_memberships


class LeastSquaresNormalize(NormalizeFitBase):
    def calculate_location(
        self,
        data: Array,
        mask: Optional[Array] = None,
        modality: Optional[str] = None,
    ) -> float:
        return 0.0

    def calculate_scale(
        self,
        data: Array,
        mask: Optional[Array] = None,
        modality: Optional[str] = None,
    ) -> float:
        tissue_membership = find_tissue_memberships(data, mask)
        tissue_means = self.tissue_means(data, tissue_membership)
        sf = self.scaling_factor(tissue_means)
        return sf

    def _fit(  # type: ignore[no-untyped-def]
        self,
        images: List[Array],
        masks: Optional[List[Array]] = None,
        modality: Optional[str] = None,
        **kwargs,
    ) -> None:
        image = images[0]  # only need one image to fit this method
        mask = masks and masks[0]
        tissue_membership = find_tissue_memberships(image, mask)
        csf_mean = np.average(image, weights=tissue_membership[..., 0])
        norm_image = (image / csf_mean) * self.norm_value
        self.standard_tissue_means = self.tissue_means(norm_image, tissue_membership)

    @staticmethod
    def tissue_means(image: Array, tissue_membership: Array) -> Vector:
        n_tissues = tissue_membership.shape[-1]
        weighted_avgs = [
            np.average(image, weights=tissue_membership[..., i])
            for i in range(n_tissues)
        ]
        return np.asarray([weighted_avgs]).T

    def scaling_factor(self, tissue_means: Vector) -> float:
        numerator = tissue_means.T @ tissue_means
        denominator = tissue_means.T @ self.standard_tissue_means
        sf: float = (numerator / denominator).item()
        return sf

    @staticmethod
    def name() -> str:
        return "lsq"

    @staticmethod
    def description() -> str:
        return (
            "Minimize distance between tissue means (CSF/GM/WM) in a "
            "least squares-sense within a set of NIfTI MR images."
        )
