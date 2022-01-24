快速开始
=============================================================================================================================================================

安装TensorDB SDK
------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
安装TensorDB SDK前，请确保Python版本大于3.71.

Windows CMD/Linux terminal输入Python后：

``python``

显示：

``Python 3.9.9 (tags/v3.9.9:ccb0e6a, Nov 15 2021, 18:08:50) [MSC v.1929 64 bit (AMD64)] on win32``

该系统中安装的Python版本为3.9.9，可安装TensorDB SDK.

输入命令：

``pip3 install pytensordb``

下载完成后即可使用。

需要注意的是由于TensorDB与前端AI模型存在强绑定关系，所以服务在启动之前需要预训练步骤，如果前端AI模型变化导致数据变化，那么需要重新进行预训练并重启服务。

连接到TensorDB
---------------------------------------------------------------------------------------------------------
需要导入的两个包：

``import vsepy as vse``

``import glob``

连接到服务器IP及端口(此处为示例IP及端口)::

    vc = vse.VseClient(('10.186.16.132', 2021))

创建数据库
---------------------------------------------------------------------------------------------------------------------------------
通过vc构造FeatureTransformer实例 ft::

    ft = vse.FeatureTransformer(client=vc)

获取数据库列表::

    all_db_lst=vc.enum_all_dbs()

创建数据库并检测数据库名是否已存在列表中::

    dbname = 'test_db1'
        if not dbname in all_db_lst:
            print("创建数据库")
            vc.create_db(dbname)
            print("创建成功")
        else:
            print("库已经存在")

枚举所有库名以及数据库记录数获取::

    all_db_lst=vc.enum_all_dbs()
        for dbname in all_db_lst:
            print(dbname, vc.get_db_record_count(dbname))

读取数据
-------------------------------------------------------------------------------------------------
从指定文件夹读取特征数据文件（二进制原始特征数据）::

    rec_idx = 1
    for fp in glob.iglob('./yizhifu/*.dat'):
        with open(fp,'rb') as f:
            raw_feat = f.read()

使用ft进行特征规范化转换::

    feat = ft.tranform(raw_feat)

将feat以及关联字段数据（binding-param-data）入库::

    binding='0|1|2|3.3|4.4|{}'.format(fp)

成功入库，返回插入的记录index::

    rec_idx = vc.push_record(dbname, feat, binding)
    print("record insert OK! idx={}".format(rec_idx))


数据检索
---------------------------------------------------------------------------------------------------------
打开data文件（注意与数据库的数据长度匹配问题）::

    with open('test.dat','rb') as f:
        raw_feat = f.read()

使用ft进行特征规范化转换::

    feat_to_retrieve = ft.tranform(raw_feat)


特征检索获取记录。返回结果存到records中::

    records = vc.retrieve_records(dbname, feat_to_retrieve)
    print("=======get retrieve results========")
    for r in records:
        print("\trec_idx={},similarity={},params={}".format(r[0],r[1],repr(r[2])))

记录与数据库的删除
-----------------------------------------------------------------------------------------------------------------------------
根据索引删除记录::

    vc.delete_record(dbname, rec_idx)
    print("删除记录成功！")
    print(dbname, vc.get_db_record_count(dbname))

数据库删除::

    vc.delete_db(dbname)
    print("数据库删除成功！")

