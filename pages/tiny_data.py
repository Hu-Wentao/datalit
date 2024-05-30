import os

import pandas as pd
import streamlit as st

_DEFAULT_DATA_FILE = './data/default.csv'


def read_file(file: str) -> pd.DataFrame:
    """读取数据文件; 不存在则新建
    :param file: 数据文件路径; 支持 csv
    :return:
    """
    os.makedirs(os.path.dirname((_abs_file := os.path.abspath(file))), exist_ok=True)
    if not os.path.isfile(_abs_file):
        return pd.DataFrame({'name': ['Zhang Example'], 'age': [666]})  # 创建Demo数据
    if (_suffix := os.path.splitext(file)[1]) == '.csv':
        return pd.read_csv(file)
    else:  # 可以支持更多类型, 但注意save同样类型的文件
        raise RuntimeError(f"尚不支持的文件类型[{_suffix}]")


def adp_data_editor_height(df_len: int, reserve=1) -> int:
    return 2 + (df_len + 1 + reserve) * 35


if __name__ == '__main__':

    def state_file(update: str = None) -> str:
        """ 文件路径
        :param update: 新文件
        :return:
        """
        if 'file' not in st.session_state:
            st.session_state['file'] = _DEFAULT_DATA_FILE
        if update:
            st.session_state['file'] = update
        return st.session_state['file']


    def state_df(update: pd.DataFrame = None, save=True) -> pd.DataFrame | None:
        """
        :param update: 更新df, 来自数据操作/文件变更
        :param save: 写入磁盘
        :return: df缓存
        """
        if 'df' not in st.session_state:  # 初始化session
            st.session_state['df'] = None
        if update is not None:
            if save:
                update.to_csv(state_file(), index=False)
            st.session_state['df'] = update
        return st.session_state['df']


    def state_meta_df(update: bool = False) -> pd.DataFrame | None:
        """
        :param update: 由于meta_df 直接来自于df, 没有持久化, 因此update用bool表达
        :return:
        """
        if 'meta_df' not in st.session_state:  # 初始化session
            st.session_state['meta_df'] = None
        if update or st.session_state['meta_df'] is None and state_df() is not None:
            meta_df = state_df().dtypes.astype(str).reset_index()
            meta_df.rename(columns={'index': 'col_name', 0: 'col_type'}, inplace=True)
            st.session_state['meta_df'] = meta_df
        return st.session_state['meta_df']


    def _on_change_open_file():
        if (open_file := st.session_state['open_file']) != state_file():  # 文件变更
            state_df(read_file(open_file), save=False)  # 刚从磁盘读取的原始数据,无需save
            state_file(open_file)  # 更新文件路径


    def _on_change_edited_df():
        change = st.session_state['edited_df']
        df = state_df()
        if edited := change['edited_rows']:  # 更新 edited rows
            for row_id, edits in edited.items():
                for col, val in edits.items():
                    df.at[row_id, col] = val
        if added := change['added_rows']:  # 添加 added rows
            df = pd.concat([df] + [pd.DataFrame(row, index=[0]) for row in added], ignore_index=True)
        if deleted := change['deleted_rows']:  # 删除 deleted rows
            df.drop(deleted, inplace=True)
        state_df(df, save=True)


    def _on_change_edited_meta_df():
        change = st.session_state['edited_meta_df']
        df = state_df()
        if edited := change['edited_rows']:  # 编辑列属性 # {2: {'col_name': 'foo'}},
            rename_cols = {df.columns[idx]: chg['col_name'] for idx, chg in edited.items() if 'col_name' in chg}
            if rename_cols:  # ==重命名列 {原列名: 新列名}
                df.rename(columns=rename_cols, inplace=True)  # {老列名:新列名}
                state_df(df, save=True)
            if retype_cols := {df.columns[idx]: chg['col_type']  # ==转换列类型 {列名: 新类型}
                               for idx, chg in edited.items() if 'col_type' in chg}:
                olds = {k: str(v) for k, v in df.dtypes.to_dict().items()}
                for col, n_type in retype_cols.items():
                    if olds[col] != n_type:
                        if n_type == 'object':
                            df[col] = df[col].astype(str, errors='ignore')
                        elif n_type == 'float64':
                            df[col] = df[col].astype(float, errors='ignore')
                        elif n_type == 'int64':
                            df[col] = df[col].astype(int, errors='ignore')
                state_df(df, save=True)
        if added := change['added_rows']:  # 新增列 [{'col_name':'bar'}]
            col_name_ls = [col['col_name'] for col in added if 'col_name' in col]
            for name in col_name_ls:
                df[name] = ""  # 默认值 “”
            state_df(df, save=True)
        if deleted := change['deleted_rows']:  # 删除列 [1,2,3]
            df.drop(df.columns[deleted], axis='columns', inplace=True)
            state_df(df, save=True)


    """### CSV数据管理"""
    with st.expander("数据源", expanded=True):
        st.text_input("文件路径", key='open_file', value=_DEFAULT_DATA_FILE, on_change=_on_change_open_file)
    with st.expander("编辑列", expanded=True):
        edited_meta_df = st.data_editor(
            (_meta_df := state_meta_df()), key='edited_meta_df', use_container_width=True,
            height=adp_data_editor_height(len(_meta_df)), on_change=_on_change_edited_meta_df, num_rows="dynamic",
            column_config={'col_name': st.column_config.TextColumn(label='列名', help='编辑列名称'),
                           'col_type': st.column_config.SelectboxColumn(label='类型', help='指定类型',
                                                                        options=['object', 'float64', 'int64'])})
    with st.expander("编辑行", expanded=True):
        st.data_editor(
            (_df := state_df()), key='edited_df', use_container_width=True, height=adp_data_editor_height(len(_df)),
            on_change=_on_change_edited_df, num_rows="dynamic",
            column_config={meta['col_name']: {'type_config': {  # 参见 class TextColumnConfig(TypedDict):
                'type': 'text' if (meta['col_type'] in ['object', 'str']) else 'number'}
            } for meta in edited_meta_df.to_dict(orient='records')})
