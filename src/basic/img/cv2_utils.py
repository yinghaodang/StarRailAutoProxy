import os
from typing import Union, List

import cv2
import numpy as np
from cv2.typing import MatLike

from basic.img import MatchResult, MatchResultList
from basic.log_utils import log


feature_detector = cv2.SIFT_create()


def read_image(file_path: str) -> MatLike:
    """
    读取图片
    :param file_path: 图片路径
    :param show_result: 是否显示结果
    :return:
    """
    if not os.path.exists(file_path):
        return None
    image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
    return image


def show_image(img: MatLike,
               rects: Union[MatchResult, MatchResultList] = None,
               win_name='DEBUG',
               wait=1):
    """
    显示一张图片
    :param img: 图片
    :param rects: 需要画出来的框
    :param win_name:
    :param wait:
    :return:
    """
    to_show = img

    if rects is not None:
        to_show = img.copy()
        if type(rects) == MatchResult:
            cv2.rectangle(to_show, (rects.x, rects.y), (rects.x + rects.w, rects.y + rects.h), (255, 255, 255), 1)
        elif type(rects) == MatchResultList:
            for i in rects:
                cv2.rectangle(to_show, (i.x, i.y), (i.x + i.w, i.y + i.h), (255, 255, 255), 1)

    cv2.imshow(win_name, to_show)
    cv2.waitKey(wait)


def image_rotate(img: MatLike, angle: int, show_result: bool = False):
    """
    对图片按中心进行旋转
    :param img: 原图
    :param angle: 逆时针旋转的角度
    :param show_result: 显示结果
    :return: 旋转后图片
    """
    height, width = img.shape[:2]
    center = (width // 2, height // 2)

    # 获取旋转矩阵
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # 应用旋转矩阵来旋转图像
    rotated_image = cv2.warpAffine(img, rotation_matrix, (width, height))

    if show_result:
        cv2.imshow('Result', rotated_image)

    return rotated_image


def mark_area_as_transparent(image: MatLike, pos: Union[List, np.ndarray], outside: bool = False):
    """
    将图片的一个区域变成透明 然后返回新的图片
    :param image: 原图
    :param pos: 区域坐标 如果是矩形 传入 [x,y,w,h] 如果是圆形 传入 [x,y,r]。其他数组长度不处理
    :param outside: 是否将区域外变成透明
    :return: 新图
    """
    # 创建一个与图像大小相同的掩膜，用于指定要变成透明的区域
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    if not type(pos) is np.ndarray:
        pos = np.array([pos])
    for p in pos:
        if len(p) == 4:
            x, y, w, h = p[0], p[1], p[2], p[3]
            # 非零像素表示要变成透明的区域
            cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        if len(p) == 3:
            x, y, r = p[0], p[1], p[2]
            # 非零像素表示要变成透明的区域
            cv2.circle(mask, (x, y), r, 255, -1)
    # 合并
    return cv2.bitwise_and(image, image, mask=mask if outside else cv2.bitwise_not(mask))


def mark_area_as_color(image: MatLike, pos: List, color, new_image: bool = False):
    """
    将图片的一个区域变颜色 然后返回新的图片
    :param image: 原图
    :param pos: 区域坐标 如果是矩形 传入 [x,y,w,h] 如果是圆形 传入 [x,y,r]。其他数组长度不处理
    :param new_image: 是否返回一张新的图
    :return: 新图
    """
    to_paint = image.copy() if new_image else image
    if not type(pos) is np.ndarray:
        pos = np.array([pos])
    for p in pos:
        if len(p) == 4:
            x, y, w, h = p[0], p[1], p[2], p[3]
            cv2.rectangle(to_paint, pt1=(x, y), pt2=(x + w, y + h), color=color, thickness=-1)
        if len(p) == 3:
            x, y, r = p[0], p[1], p[2]
            cv2.circle(to_paint, (x, y), r, color, -1)
    return to_paint


def match_template(source: MatLike, template: MatLike, threshold,
                   mask: np.ndarray = None, ignore_inf: bool = False) -> MatchResultList:
    """
    在原图中匹配模板 注意无法从负偏移量开始匹配 即需要保证目标模板不会在原图边缘位置导致匹配不到
    :param source: 原图
    :param template: 模板
    :param threshold: 阈值
    :param mask: 掩码
    :param ignore_inf: 是否忽略无限大的结果
    :return: 所有匹配结果
    """
    tx, ty = template.shape[1], template.shape[0]
    # 进行模板匹配
    result = cv2.matchTemplate(source, template, cv2.TM_CCOEFF_NORMED, mask=mask)

    match_result_list = MatchResultList()
    filtered_locations = np.where(np.logical_and(
        result >= threshold,
        np.isfinite(result) if ignore_inf else np.ones_like(result))
    )  # 过滤低置信度的匹配结果

    # 遍历所有匹配结果，并输出位置和置信度
    for pt in zip(*filtered_locations[::-1]):
        confidence = result[pt[1], pt[0]]  # 获取置信度
        match_result_list.append(MatchResult(confidence, pt[0], pt[1], tx, ty))

    return match_result_list


def concat_vertically(img: MatLike, next_img: MatLike, decision_height: int = 200):
    """
    垂直拼接图片。
    假设两张图片是通过垂直滚动得到的，即宽度一样，部分内容重叠
    :param img: 图
    :param next_img: 下一张图
    :decision_height: 用第二张图的多少高度来判断重叠部分
    :return:
    """
    # 截取一个横截面用来匹配
    next_part = next_img[0: decision_height, :]
    result = match_template(img, next_part, 0.5)
    # 找出置信度最高的结果
    r = None
    for i in result:
        if r is None or i.confidence > r.confidence:
            r = i
    h, w, _ = img.shape
    overlap_h = h - r.y
    extra_part = next_img[overlap_h+1:,:]
    # 垂直拼接两张图像
    return cv2.vconcat([img, extra_part])


def concat_horizontally(img: MatLike, next_img: MatLike, decision_width: int = 200):
    """
    水平拼接图片。
    假设两张图片是通过水平滚动得到的，即高度一样，部分内容重叠
    :param img: 图
    :param next_img: 下一张图
    :param decision_width: 用第二张图的多少宽度来判断重叠部分
    :return:
    """
    # 截取一个横截面用来匹配
    next_part = next_img[:, 0: decision_width]
    result = match_template(img, next_part, 0.5)
    # 找出置信度最高的结果
    r = result.max
    h, w, _ = img.shape
    overlap_w = w - r.x
    extra_part = next_img[:, overlap_w+1:]
    # 水平拼接两张图像
    return cv2.hconcat([img, extra_part])


def is_same_image(i1, i2, threshold: float = 1) -> bool:
    """
    简单使用均方差判断两图是否一致
    :param i1: 图1
    :param i2: 图2
    :param threshold: 低于阈值认为是相等
    :return: 是否同一张图
    """
    return np.mean((i1 - i2) ** 2) < threshold


def color_similarity_2d(image, color):
    """
    PhotoShop 魔棒功能的容差是一样的，颜色差值 = abs(max(RGB差值)) + abs(min(RGB差值))
    感谢 https://github.com/LmeSzinc/StarRailCopilot/wiki/MinimapTracking
    :param image:
    :param color:
    :return:
    """
    b, g, r = cv2.split(cv2.subtract(image, (*color, 0)))
    positive = cv2.max(cv2.max(r, g), b)
    b, g, r = cv2.split(cv2.subtract((*color, 0), image))
    negative = cv2.max(cv2.max(r, g), b)
    return cv2.subtract(255, cv2.add(positive, negative))


def show_overlap(source, template, x, y, template_scale: float = 1, win_name: str = 'DEBUG', wait: int = 1):
    to_show_source = source.copy()

    if template_scale != 1:
        # 缩放后的宽度和高度
        scaled_width = int(template.shape[1] * template_scale)
        scaled_height = int(template.shape[0] * template_scale)

        # 缩放小图
        to_show_template = cv2.resize(template, (scaled_width, scaled_height))
    else:
        to_show_template = template

    source_overlap_template(to_show_source, to_show_template, x, y)
    show_image(to_show_source, win_name=win_name, wait=wait)


def feature_detect_and_compute(img: MatLike, mask: MatLike = None):
    return feature_detector.detectAndCompute(img, mask=mask)


def feature_keypoints_to_np(keypoints):
    return np.array([(kp.pt[0], kp.pt[1], kp.size, kp.angle, kp.response, kp.octave, kp.class_id) for kp in keypoints])


def feature_keypoints_from_np(np_arr):
    return np.array([cv2.KeyPoint(x=kp[0], y=kp[1], size=kp[2], angle=kp[3],
                                  response=kp[4], octave=int(kp[5]), class_id=int(kp[6])) for kp in np_arr])


def feature_match(source_kp, source_desc, template_kp, template_desc, source_mask):
    if len(source_kp) == 0 or len(template_kp) == 0:
        return None, None, None, None

    # feature_matcher = cv2.FlannBasedMatcher()
    feature_matcher = cv2.BFMatcher()
    matches = feature_matcher.knnMatch(template_desc, source_desc, k=2)
    # 应用比值测试，筛选匹配点
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    if len(good_matches) < 4:  # 不足4个优秀匹配点时 不能使用RANSAC
        return good_matches, None, None, None

    # 提取匹配点的坐标
    template_points = np.float32([template_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)  # 模板的
    source_points = np.float32([source_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)  # 原图的

    # 使用RANSAC算法估计模板位置和尺度
    _, mask = cv2.findHomography(template_points, source_points, cv2.RANSAC, 5.0, mask=source_mask)
    # 获取内点的索引 拿最高置信度的
    inlier_indices = np.where(mask.ravel() == 1)[0]
    if len(inlier_indices) == 0:  # mask 里没找到就算了 再用good_matches的结果也是很不准的
        return good_matches, None, None, None

    # 距离最短 置信度最高的结果
    best_match = None
    for i in range(len(good_matches)):
        if mask[i] == 1 and (best_match is None or good_matches[i].distance < best_match.distance):
            best_match = good_matches[i]

    query_point = source_kp[best_match.trainIdx].pt  # 原图中的关键点坐标 (x, y)
    train_point = template_kp[best_match.queryIdx].pt  # 模板中的关键点坐标 (x, y)

    # 获取最佳匹配的特征点的缩放比例
    query_scale = source_kp[best_match.trainIdx].size
    train_scale = template_kp[best_match.queryIdx].size
    template_scale = query_scale / train_scale

    # 模板图缩放后在原图上的偏移量
    offset_x = query_point[0] - train_point[0] * template_scale
    offset_y = query_point[1] - train_point[1] * template_scale

    return good_matches, offset_x, offset_y, template_scale


def connection_erase(mask: MatLike, threshold: int = 50, erase_white: bool = True,
                     connectivity: int = 8) -> MatLike:
    """
    通过连通性检测 消除一些噪点
    :param mask: 黑白图 掩码图
    :param threshold: 小于多少连通时 认为是噪点
    :param erase_white: 是否清除白色
    :param connectivity: 连通性检测方向 4 or 8
    :return: 消除噪点后的图
    """
    to_check_connection = mask if erase_white else cv2.bitwise_not(mask)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(to_check_connection, connectivity=connectivity)
    large_components = []
    for label in range(1, num_labels):
        if stats[label, cv2.CC_STAT_AREA] < threshold:
            large_components.append(label)

    result = mask.copy()
    for label in large_components:
        result[labels == label] = 0 if erase_white else 255

    return result


def crop_image(img, rect: tuple, copy: bool = False):
    """
    裁剪图片
    :param img: 原图
    :param rect: 裁剪区域 (x1, y1, x2, y2)
    :param copy: 是否复制新图
    :return: 裁剪后图片
    """
    x1, y1, x2, y2 = rect
    if x1 < 0:
        x1 = 0
    if x2 > img.shape[1]:
        x2 = img.shape[1]
    if y1 < 0:
        y1 = 0
    if y2 > img.shape[0]:
        y2 = img.shape[0]

    x1, y1 = int(x1), int(y1)
    x2, y2 = int(x2), int(y2)
    crop = img[y1: y2, x1: x2]
    return crop.copy() if copy else crop


def dilate(img, k):
    """
    膨胀一下 适合掩码图
    :param img:
    :param k:
    :return:
    """
    kernel = np.ones((k, k), np.uint8)
    return cv2.dilate(src=img, kernel=kernel, iterations=1)


def convert_to_standard(origin, mask, width: int = 51, height: int = 51, bg_color=None):
    """
    转化成 目标尺寸并居中
    :param origin:
    :param mask:
    :param width: 目标尺寸宽度
    :param height: 目标尺寸高度
    :param bg_color: 背景色
    :return:
    """
    bw = np.where(mask == 255)
    white_pixel_coordinates = list(zip(bw[1], bw[0]))

    # 找到最大最小坐标值
    max_x = max(white_pixel_coordinates, key=lambda i: i[0])[0]
    max_y = max(white_pixel_coordinates, key=lambda i: i[1])[1]

    min_x = min(white_pixel_coordinates, key=lambda i: i[0])[0]
    min_y = min(white_pixel_coordinates, key=lambda i: i[1])[1]

    # 稍微扩大一下范围
    if max_x < mask.shape[1]:
        max_x += min(5, mask.shape[1] - max_x)
    if max_y < mask.shape[0]:
        max_y += min(5, mask.shape[0] - max_y)
    if min_x > 0:
        min_x -= min(5, min_x)
    if min_y > 0:
        min_y -= min(5, min_y)

    cx = (min_x + max_x) // 2
    cy = (min_y + max_y) // 2

    x1, y1 = cx - min_x, cy - min_y
    x2, y2 = max_x - cx, max_y - cy

    ccx = width // 2
    ccy = height // 2

    # 移动到 50*50 居中
    final_mask = np.zeros((height, width), dtype=np.uint8)
    final_mask[ccy-y1:ccy+y2, ccx-x1:ccx+x2] = mask[min_y:max_y, min_x:max_x]

    if len(origin.shape) > 2:
        final_origin = np.zeros((height, width, 3), dtype=np.uint8)
        final_origin[ccy-y1:ccy+y2, ccx-x1:ccx+x2, :] = origin[min_y:max_y, min_x:max_x, :]
    else:
        final_origin = np.zeros((height, width), dtype=np.uint8)
        final_origin[ccy - y1:ccy + y2, ccx - x1:ccx + x2] = origin[min_y:max_y, min_x:max_x]
    final_origin = cv2.bitwise_and(final_origin, final_origin, mask=final_mask)

    if bg_color is not None:  # 部分图标可以背景统一使用颜色
        final_origin[np.where(final_mask == 0)] = bg_color

    return final_origin, final_mask


def source_overlap_template(source, template, x, y, copy_img: bool = False):
    """
    在原图上覆盖模板图
    :param source: 原图
    :param template: 模板图 缩放后
    :param x: 偏移量
    :param y: 偏移量
    :param copy_img: 是否复制新图片
    :return:
    """
    to_overlap_source = source.copy() if copy_img else source

    rect1, rect2 = get_overlap_rect(source, template, x, y)
    sx_start, sy_start, sx_end, sy_end = rect1
    tx_start, ty_start, tx_end, ty_end = rect2

    # 将覆盖图像放置到底图的指定位置
    to_overlap_source[sy_start:sy_end, sx_start:sx_end] = template[ty_start:ty_end, tx_start:tx_end]

    return to_overlap_source


def get_overlap_rect(source, template, x, y):
    """
    根据模板图在原图上的偏移量 计算出覆盖区域
    :param source: 原图
    :param template: 模板图 缩放后
    :param x: 偏移量
    :param y: 偏移量
    :return:
    """
    # 获取要覆盖图像的宽度和高度
    overlay_height, overlay_width = template.shape[:2]

    # 覆盖图在原图上的坐标
    sx_start = int(x)
    sy_start = int(y)
    sx_end = sx_start + overlay_width
    sy_end = sy_start + overlay_height

    # 覆盖图要用的坐标
    tx_start = 0
    ty_start = 0
    tx_end = overlay_width
    ty_end = overlay_height

    # 覆盖图缩放后可以超出了原图的范围
    if sx_start < 0:
        tx_start -= sx_start
        sx_start -= sx_start
    if sx_end > source.shape[1]:
        tx_end -= sx_end - source.shape[1]
        sx_end -= sx_end - source.shape[1]

    if sy_start < 0:
        ty_start -= sy_start
        sy_start -= sy_start
    if sy_end > source.shape[0]:
        ty_end -= sy_end - source.shape[0]
        sy_end -= sy_end - source.shape[0]

    return (sx_start, sy_start, sx_end, sy_end), (tx_start, ty_start, tx_end, ty_end)
