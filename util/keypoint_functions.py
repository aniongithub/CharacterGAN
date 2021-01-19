import numpy as np
import skimage
from skimage import color, filters, morphology
import os
import cv2

from options import keypoints as keypoint_dict


def get_keypoint_colors():
    return keypoint_dict.get_keypoint_colors()


def get_keypoint_labels():
    return keypoint_dict.get_keypoints_label()


def get_keypoints():
    return keypoint_dict.get_keypoints()


# add a connecting line between keypoints
def add_skeleton(kps_2d, kps_1d, skeleton):
    for idx in kps_1d.keys():
        start_x = int(kps_1d[idx][0])
        start_y = int(kps_1d[idx][1])
        if start_x < 0:
            start_x = 0
        if start_x >= 250:
            start_x = 249
        if start_y < 0:
            start_y = 0
        if start_y >= 250:
            start_y = 249
        for end in skeleton[idx]:
            end_x = int(kps_1d[end][0])
            end_y = int(kps_1d[end][1])
            if end_x < 0:
                end_x = 0
            if end_x >= 250:
                end_x = 249
            if end_y < 0:
                end_y = 0
            if end_y >= 250:
                end_y = 249
            line_x, line_y = weighted_line(start_x, start_y, end_x, end_y, rmin=0, rmax=max(kps_2d.shape[1:]))
            kps_2d[:, line_y, line_x] = 1
    return kps_2d



def load_keypoints(opt):
    with open(os.path.join(opt.dataroot, "keypoints.csv"), "r") as f:
        keypoints = f.readlines()
    keypoint_labels = keypoint_dict.get_keypoints()

    kp_dict = {}
    for line_idx, keypoint in enumerate(keypoints):
        # check keypoint entry has correct format
        if len(keypoint.split(",")) != 6:
            print("Keypoint file has not enough columns ({} columns) at line {}.".format(len(keypoint.split(",")), line_idx))
            print("Keypoint file should have six columns: keypoint,x-coord,y-coord,img-name,img-resolution-x,img-resolution-y")
            exit()

        # load keypoints
        kp, x, y, img, _, _ = keypoint.split(",")
        if img not in kp_dict.keys():
            kp_dict[img] = {keypoint_labels[kp]: [int(x),int(y)]}
        else:
            kp_dict[img][keypoint_labels[kp]] = [int(x),int(y)]

    # check every image has all keypoints
    for k1 in kp_dict.keys():
        if len(kp_dict[k1].keys()) != opt.num_keypoints:
            print("Keypoints wrong for: {} (found {} keypoints instead of {}).".format(k1, len(kp_dict[k1].keys()), opt.num_keypoints))
            exit()

    return kp_dict


def load_skeleton_info(opt):
    keypoint_labels = keypoint_dict.get_keypoints()
    skeleton = {}
    with open(os.path.join(opt.dataroot, "keypoints_skeleton.csv"), "r") as f:
        skeleton_info = f.readlines()

    for info in skeleton_info:
        entries = info.strip().split(",")
        start = entries[0]
        ends = entries[1:]
        skeleton[keypoint_labels[start]] = [keypoint_labels[ends[0]]]
        for end in ends[1:]:
            if end == "":
                break
            skeleton[keypoint_labels[start]].append(keypoint_labels[end])

    return skeleton


def create_keypoint_condition(img, keypoints, opt, num_keypoints, gaussian_blur=True, normalize=True):
    height, width, _ = img.shape
    condition = np.zeros([num_keypoints, height, width], dtype=np.float32)

    for idx, kp in enumerate(sorted(keypoints.keys())):
        x, y = keypoints[kp]
        x = int(x)
        y = int(y)
        condition[idx, y-2:y+2, x-2:x+2] = 1
    if gaussian_blur:
        radius = int(opt.gaussian_r * max(height, width))
        sigma = int(opt.gaussian_s * max(height, width))
        element = skimage.morphology.disk(radius=radius)
        for idx in range(num_keypoints):
            _mask = condition[idx, :, :]
            _mask = cv2.dilate(_mask, element, iterations=1)
            _mask = filters.gaussian(_mask, sigma=sigma)
            condition[idx, :, :] = _mask

    if normalize:
        condition = 2 * (condition / np.max(condition) - 0.5)

    return condition


def apply_gaussian_blur(condition, opt, normalize=True, size=250):
    radius = int(opt.gaussian_r * max(size, size))
    sigma = int(opt.gaussian_s * max(size, size))
    element = skimage.morphology.disk(radius=radius)
    for idx in range(opt.num_keypoints):
        _mask = condition[idx, :, :]
        _mask = cv2.dilate(_mask, element, iterations=1)
        _mask = filters.gaussian(_mask, sigma=sigma)
        condition[idx, :, :] = _mask
    if normalize:
        condition = 2 * (condition / np.max(condition) - 0.5)

    return condition


def trapez(y,y0,w):
    return np.clip(np.minimum(y+1+w/2-y0, -y+1+w/2+y0),0,1)


def weighted_line(r0, c0, r1, c1, w=2, rmin=0, rmax=np.inf):
    # The algorithm below works fine if c1 >= c0 and c1-c0 >= abs(r1-r0).
    # If either of these cases are violated, do some switches.
    if abs(c1-c0) < abs(r1-r0):
        # Switch x and y, and switch again when returning.
        xx, yy = weighted_line(c0, r0, c1, r1, w, rmin=rmin, rmax=rmax)
        return yy, xx

    # At this point we know that the distance in columns (x) is greater
    # than that in rows (y). Possibly one more switch if c0 > c1.
    if c0 > c1:
        return weighted_line(r1, c1, r0, c0, w, rmin=rmin, rmax=rmax)

    # The following is now always < 1 in abs
    if c1 - c0 == 0:
        c1 = c1 + 1
        slope = (r1-r0) / (c1-c0)
    else:
        slope = (r1-r0) / (c1-c0)

    # Adjust weight by the slope
    w *= np.sqrt(1+np.abs(slope)) / 2

    # We write y as a function of x, because the slope is always <= 1
    # (in absolute value)
    x = np.arange(c0, c1+1, dtype=float)
    y = x * slope + (c1*r0-c0*r1) / (c1-c0)

    # Now instead of 2 values for y, we have 2*np.ceil(w/2).
    # All values are 1 except the upmost and bottommost.
    thickness = np.ceil(w/2)
    yy = (np.floor(y).reshape(-1,1) + np.arange(-thickness-1,thickness+2).reshape(1,-1))
    xx = np.repeat(x, yy.shape[1])

    yy = yy.flatten()

    # Exclude useless parts and those outside of the interval
    # to avoid parts outside of the picture
    mask = np.logical_and.reduce((yy >= rmin, yy < rmax))

    return yy[mask].astype(int), xx[mask].astype(int)