# coding=utf-8
import vsepy as vse
import glob


if __name__=="__main__":
    print("配置连接地址")
    vc = vse.VseClient(('10.186.16.132', 2021))
    # 通过vc构造FeatureTransformer实例 ft
    ft = vse.FeatureTransformer(client=vc)
    # 打印ft参数
    print(ft)

    all_db_lst=vc.enum_all_dbs()

    '''步骤1：建库'''
    dbname = 'test_db1'
    if not dbname in all_db_lst:
        # 数据库创建
        print("创建数据库")
        vc.create_db(dbname)
        print("创建成功")
    else:
        print("库已经存在")

    # 枚举所有库
    all_db_lst=vc.enum_all_dbs()
    for dbname in all_db_lst:
        # 打印库名, 以及数据库记录数获取
        print(dbname, vc.get_db_record_count(dbname))
    
    # 从指定文件夹读取特征数据文件（二进制原始特征数据）
    rec_idx = 1
    for fp in glob.iglob('./yizhifu/*.dat'):
        with open(fp,'rb') as f:
            raw_feat = f.read()
        # 使用ft进行特征规范化转换
        feat = ft.tranform(raw_feat)
        '''
        将feat以及关联字段数据（binding-param-data）入库
        '''
        binding='0|1|2|3.3|4.4|{}'.format(fp)
        # 成功入库，返回插入的记录index 
        rec_idx = vc.push_record(dbname, feat, binding)
        print("record insert OK! idx={}".format(rec_idx))
    
    print(dbname, vc.get_db_record_count(dbname))

    '''步骤3：检索'''
    with open('test.dat','rb') as f:
        raw_feat = f.read()
    # 使用ft进行特征规范化转换
    feat_to_retrieve = ft.tranform(raw_feat)
    # 特征检索获取记录。返回结果存到records中
    records = vc.retrieve_records(dbname, feat_to_retrieve)
    print("=======get retrieve results========")
    for r in records:
        print("\trec_idx={},similarity={},params={}".format(r[0],r[1],repr(r[2])))
    
    # 根据索引删除记录
    vc.delete_record(dbname, rec_idx)
    print("删除记录成功！")
    print(dbname, vc.get_db_record_count(dbname))
    # 数据库删除
    vc.delete_db(dbname)
    print("数据库删除成功！")