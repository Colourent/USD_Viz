from pxr import Usd, UsdGeom, Gf, Sdf, UsdShade
import random


usd_file_path = "/home/taoranlu/USD/yinhe_demo_0107/Collected_ShelfDemo_remove_simstep/ShelfDemo_vis.usd" # change to your path to usd file


stage = Usd.Stage.Open(usd_file_path)
if not stage:
    print("无法打开USD文件:", usd_file_path)

def create_bbox_for_mesh(stage, mesh_prim):
    mesh_path = str(mesh_prim.GetPath())

    # 添加调试信息
    print(f"\n处理: {mesh_path}")

    # 获取mesh数据
    mesh = UsdGeom.Mesh(mesh_prim)
    points = mesh.GetPointsAttr().Get()

    if not points:
        print(f"警告: {mesh_path} 没有点数据")
        return

    # 考虑transform
    xform = UsdGeom.XformCommonAPI(mesh_prim)
    translation, rotation, scale, pivot, _ = xform.GetXformVectors(Usd.TimeCode.Default())

    # 打印变换信息
    print(f"Translation: {translation}")
    print(f"Scale: {scale}")

    # 计算边界框
    bbox_min = Gf.Vec3f(float('inf'), float('inf'), float('inf'))
    bbox_max = Gf.Vec3f(float('-inf'), float('-inf'), float('-inf'))

    for point in points:
        # 移除scale的影响
        transformed_point = Gf.Vec3f(point[0], point[1], point[2])

        bbox_min = Gf.Vec3f(min(bbox_min[0], transformed_point[0]),
                           min(bbox_min[1], transformed_point[1]),
                           min(bbox_min[2], transformed_point[2]))
        bbox_max = Gf.Vec3f(max(bbox_max[0], transformed_point[0]),
                           max(bbox_max[1], transformed_point[1]),
                           max(bbox_max[2], transformed_point[2]))

    # 计算size和center
    size = (bbox_max - bbox_min) / 2.0
    center = (bbox_max + bbox_min) / 2.0

    # 打印边界框信息
    print(f"BBox Min: {bbox_min}")
    print(f"BBox Max: {bbox_max}")
    print(f"Size: {size}")
    print(f"Center: {center}")

    # 添加安全检查
    max_allowed_size = 1000  # 设置一个合理的最大尺寸
    if any(abs(s) > max_allowed_size for s in size):
        print(f"警告: {mesh_path} 的边界框尺寸异常大")
        # 可以选择跳过这个物体或使用默认尺寸
        size = Gf.Vec3f(1.0, 1.0, 1.0)  # 使用默认尺寸

    # 修改bbox的创建路径，直接使用mesh_prim的xform
    bbox_path = f"{mesh_path}/bbox"  # 直接在mesh下创建bbox

    bbox_prim = UsdGeom.Cube.Define(stage, bbox_path)

    # 直接设置Display Color为绿色
    bbox_prim.CreateDisplayColorAttr([Gf.Vec3f(0.0, 1.0, 0.0)])  # RGB: 纯绿色

    # 设置默认不可见
    bbox_prim.CreateVisibilityAttr().Set('invisible')

    # 设置transform
    bbox_xform = UsdGeom.XformCommonAPI(bbox_prim)
    bbox_xform.SetTranslate((0, 0, 0))
    bbox_xform.SetRotate((0, 0, 0))
    bbox_xform.SetScale((size[0], size[1], size[2]))

    # 使用一个统一的材质路径，而不是为每个box创建新材质
    material_path = "/World/SharedMaterials/GreenBoxMaterial"

    # 如果共享材质不存在，创建它
    if not stage.GetPrimAtPath(material_path):
        material = create_glass_material(stage, material_path)
    else:
        material = UsdShade.Material.Get(stage, material_path)

    # 确保材质绑定
    bbox_prim.GetPrim().ApplyAPI(UsdShade.MaterialBindingAPI)
    UsdShade.MaterialBindingAPI(bbox_prim).Bind(material)

    # 添加调试信息
    bound_material = UsdShade.MaterialBindingAPI(bbox_prim).GetDirectBinding().GetMaterial()
    print(f"Box: {bbox_path}")
    print(f"Bound material: {bound_material.GetPath() if bound_material else 'None'}")

    return bbox_prim

def create_glass_material(stage, material_path):
    """创建统一的白色不透明材质"""
    # 如果材质已存在，先删除确保重新创建
    if stage.GetPrimAtPath(material_path):
        stage.RemovePrim(material_path)

    material = UsdShade.Material.Define(stage, material_path)
    pbrShader = UsdShade.Shader.Define(stage, f"{material_path}/PBRShader")

    # 使用更简单的材质设置
    pbrShader.CreateIdAttr("UsdPreviewSurface")
    pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(1.0, 1.0, 1.0))  # 纯白色
    pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.8)
    pbrShader.CreateInput("specularColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))  # 无镜面反射

    material.CreateSurfaceOutput().ConnectToSource(pbrShader.ConnectableAPI(), "surface")
    return material

# 主循环
# 首先收集所有Bottle的prim
bottle_prims = []
for prim in stage.Traverse():
    if UsdGeom.Mesh(prim) and "Store" in str(prim.GetPath()):
        bottle_prims.append(prim)

# 如果Bottle数量超过100个，随机选择100个
if len(bottle_prims) > 100:
    selected_prims = random.sample(bottle_prims, 100)
else:
    selected_prims = bottle_prims

# 为选中的Bottle创建bbox
bbox_count = 0
print(f"\n总共找到 {len(bottle_prims)} 个Bottle，将随机处理其中100个")
print("-" * 50)

for prim in selected_prims:
    bbox = create_bbox_for_mesh(stage, prim)
    if bbox:
        bbox_count += 1

print(f"\n成功创建了 {bbox_count} 个Bottle边界框")

# 保存更新后的stage
stage.Save()
