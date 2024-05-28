import os
from typing import Optional

import pandas as pd
import streamlit as st


def read_file(file: str, create=True, object_as_str=True) -> pd.DataFrame:
    """读取数据文件
    :param object_as_str: 空白的object列将被识别为str
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
        _df = pd.read_csv(file)
        if object_as_str:
            # 将所有 object 类型的列转换成 str 类型
            print("debug1#\n", _df.dtypes)
            object_columns = _df.select_dtypes(include=['object']).columns
            _df[object_columns] = _df[object_columns].astype(str)
            print("debug2#\n", _df.dtypes)
        return _df
    else:
        raise RuntimeError(f"尚不支持的文件[{_suffix}]")


if __name__ == '__main__':
    _DEFAULT_CSV = './data/default.csv'

    if 'df' not in st.session_state:
        st.session_state['df'] = None
    #  key='file_path'
    if 'state_save_df' not in st.session_state:
        st.session_state['state_save_df'] = False


    def state_df() -> Optional[pd.DataFrame]:
        """暂存df, 无需频繁读写磁盘"""
        if (_df := st.session_state['df']) is None and (file_path := st.session_state['file_path']) is not None:
            # 未读取df,且已经设置文件路径, 则读取文件
            # print("read_file#", file_path)
            _df = read_file(file_path, create=False, object_as_str=False)
            st.session_state['df'] = _df
        return _df


    def state_save_df(value=None) -> bool:
        if value is not None:
            st.session_state['state_save_df'] = value
        return st.session_state['state_save_df']


    def save_df(force=False):
        if state_save_df() or force:
            # edited_df.to_csv(st.session_state['file_path'], index=False)
            df.to_csv(st.session_state['file_path'], index=False)
            state_save_df(value=False)


    def _on_change_edited_meta_df():
        change = st.session_state['edited_meta_df']
        edited: dict[int, dict] = change['edited_rows']  # dict[`index`:Series]
        added: list[dict] = change['added_rows']  # list[Series]
        deleted: list[int] = change['deleted_rows']  # list[`df index`]
        need_save = False
        if edited:  # 编辑列属性 # {2: {'col_name': 'foo'}},
            rename_cols = {df.columns[idx]: chg['col_name'] for idx, chg in edited.items() if 'col_name' in chg}
            # {老列名: 新列名}
            if rename_cols:  # {老列名:新列名}
                df.rename(columns=rename_cols, inplace=True)  # {老列名:新列名}
                need_save = True
            # {列名: 新类型}
            if retype_cols := {df.columns[idx]: chg['col_type'] for idx, chg in edited.items() if 'col_type' in chg}:
                print("retype_cols#", retype_cols)
                olds = {k: str(v) for k, v in df.dtypes.to_dict().items()}
                for col, n_type in retype_cols.items():
                    if olds[col] != n_type:
                        if n_type == 'object':
                            df[col] = df[col].astype(str)
                        elif n_type == 'float64':
                            df[col] = df[col].astype(float)
                        elif n_type == 'int64':
                            df[col] = df[col].astype(int)
                need_save = True
                pass
        if added:  # 新增列 [{'col_name':'bar'}]
            col_name_ls = [col['col_name'] for col in added if 'col_name' in col]
            for name in col_name_ls:
                df[name] = ""  # 默认值 “”
            need_save = True
            pass
        if deleted:  # [1,2,3]
            df.drop(df.columns[deleted], axis='columns', inplace=True)
            need_save = True

        if need_save:
            save_df()
            # df.to_csv(csv_file, index=False)  # 直接保存到磁盘
        pass


    def _on_change_edited_df(force=False):
        change = st.session_state['edited_df']
        edited: dict[int, dict] = change['edited_rows']  # dict[`index`:Series]
        added: list[dict] = change['added_rows']  # list[Series]
        deleted: list[int] = change['deleted_rows']  # list[`df index`]

        if not force and added == [{}]:  # ignore add blank
            return
        state_save_df(value=True)


    # =====
    """
    ### 管理数据
    """
    with st.expander("数据源", expanded=True):
        # file_path = st.text_input("文件路径", value=_DEFAULT_CSV)
        st.text_input("文件路径", key='file_path', value=_DEFAULT_CSV)

    df = state_df()

    """---"""
    with st.expander("编辑列", expanded=True):
        meta_df = df.dtypes.astype(str).reset_index()
        meta_df.rename(columns={'index': 'col_name', 0: 'col_type'}, inplace=True)

        edited_meta_df = st.data_editor(
            meta_df, key='edited_meta_df', use_container_width=True,
            height=72 + len(meta_df) * 35, num_rows="dynamic", on_change=_on_change_edited_meta_df,
            column_config={
                'col_name': st.column_config.TextColumn(label='列名', help='编辑列名称'),
                'col_type': st.column_config.SelectboxColumn(label='类型', help='指定类型',
                                                             options=['object', 'float64', 'int64']),
            }
        )
    _cols = df.select_dtypes(include=['object', 'float64', 'int64']).columns
    if len(_cols) > 0:
        df[_cols] = df[_cols].astype(str)  # 便于editor编辑内容
    df = st.data_editor(
        df, key='edited_df', use_container_width=True, height=2 + (len(df) + 2) * 35,
        on_change=_on_change_edited_df, num_rows="dynamic",
        column_config={
            meta['col_name']: {
                # 'label': None,  # None则用列名
                # 'width': None,  # "small", "medium", "large", or None(sized fit)
                # 'help': 'msg'
                # 'disabled': False, # 默认False
                # 'required': False, # 默认False
                # 'default': meta['default_val'],  # value # str, bool, int, float, or None; 设置默认值
                # 'value' # str, bool, int, float, or None; 设置默认值
                # 'hidden': False #  bool or None, 默认False
                'type_config': {  # 参见 class TextColumnConfig(TypedDict):
                    'type': 'text' if (meta['col_type'] in ['object', 'str']) else 'number'
                }
            } for meta in edited_meta_df.to_dict(orient='records')
        }
    )

    save_df()

    # if st.button("手动保存"):
    #     save_df(force=True)
