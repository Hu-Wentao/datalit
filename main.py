import os

import pandas as pd
import streamlit as st


def read_file(file: str, create=True) -> pd.DataFrame:
    """读取数据文件
    :param file: 数据文件路径
    :param create: True 不存在则创建
    :return:
    """
    _abs_file = os.path.abspath(file)
    _path = os.path.dirname(_abs_file)
    if not os.path.exists(_path):
        if create:
            os.makedirs(_path)
        else:
            raise RuntimeError(f"路径不存在[{_path}]")

    if not os.path.isfile(_abs_file):
        if create:
            return pd.DataFrame({'column1': [], 'column2': []})
        else:
            raise RuntimeError(f"文件不存在[{file}]")

    _suffix = os.path.splitext(file)[1]
    if _suffix == '.csv':
        return pd.read_csv(file)
    else:
        raise RuntimeError(f"尚不支持的文件[{_suffix}]")


if __name__ == '__main__':
    _DEFAULT_CSV = './default.csv'

    if 'edited' not in st.session_state:
        st.session_state['edited'] = False


    def _data_changed():
        st.session_state['edited'] = True


    # =====
    """
    ### 管理数据
    """

    csv_file = st.text_input("csv文件", value=_DEFAULT_CSV)
    df = read_file(csv_file)
    #

    """---"""
    with st.expander("新增列"):
        name = st.text_input("新增列名")
        col_type = st.selectbox("类型", options=["str", "int", "float"], index=0)

        # default_value = st.text_input("填充值")
        if len(name) > 0:
            c1, c2 = st.columns([4, 1])
            with c1:
                st.info(f"新增列 {name} : {col_type}")
            with c2:
                if st.button("新增"):
                    _value = {
                        "str": " ",
                        "int": 0,
                        "float": 0.0,
                    }
                    df[name] = _value[col_type]
                    _data_changed()
    with st.expander("编辑列"):
        """重命名/删除列"""
        cols = pd.DataFrame({'name': df.columns})
        cols['n_name'] = None
        cols['delete'] = False

        n_cols = st.data_editor(
            cols, use_container_width=True, height=60 + len(cols) * 35,
            column_config={
                'name': st.column_config.TextColumn(label='列名', help=''),
                'n_name': st.column_config.TextColumn(label='重命名', help='设置新的名称'),
                'delete': st.column_config.CheckboxColumn(
                    label='删除', help='删除列',
                ),
            }
        )
        # 处理删除 ====
        del_col = n_cols.loc[n_cols['delete'] == True]
        if len(del_col) > 0:
            _cols = del_col['name'].values
            c1, c2 = st.columns([4, 1])
            with c1:
                st.info(f"删除列{_cols}")
            with c2:
                if st.button("删除"):
                    df.drop(_cols, axis=1, inplace=True)
                    _data_changed()
                    pass
        # 处理重命名 ====
        rename_col: pd.DataFrame = n_cols.loc[~n_cols['n_name'].isna(), ['name', 'n_name']]
        if len(rename_col) > 0:
            _rst_list = rename_col.to_dict('records')
            _rename_columns = {rst['name']: rst['n_name'] for rst in _rst_list}
            c1, c2 = st.columns([4, 1])
            with c1:
                st.info(f"重命名列{_rename_columns}")
            with c2:
                if st.button("重命名"):
                    df.rename(columns=_rename_columns, inplace=True)
                    _data_changed()
    #
    # with st.expander("视图"):
    #     st.selectbox('')

    edited = st.data_editor(
        df, use_container_width=True, height=60 + len(df) * 35,
        on_change=_data_changed,
    )
    # 保存
    if st.session_state['edited']:
        edited.to_csv(csv_file, index=False)
        st.session_state['edited'] = False
        st.rerun()
