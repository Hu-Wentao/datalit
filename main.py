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
    try:
        if (_suffix := os.path.splitext(file)[1]) == '.csv':
            return pd.read_csv(file, on_bad_lines="skip")
        else:  # 可以支持更多类型, 但注意save同样类型的文件
            raise RuntimeError(f"尚不支持的文件类型[{_suffix}]")
    except pd.errors.EmptyDataError:  # 文件存在但内容空白
        return pd.DataFrame()


def write_file(data: pd.DataFrame, file: str):
    if (_suffix := os.path.splitext(file)[1]) == '.csv':
        data.to_csv(file, index=False)
    else:
        raise RuntimeError(f"尚不支持的文件类型[{_suffix}]")


def adp_data_editor_height(df_len: int, reserve=1, least_len=2) -> int:
    if df_len < least_len:
        df_len = least_len
    return 2 + (df_len + 1 + reserve) * 35


if __name__ == '__main__':

    def state_data_file(update: str = None) -> str:
        """ data文件路径; 同时保存在session与url中
        :param update: 新文件
        :return:
        """
        if update:  # 必须放在开头, 初始化有递归调用
            # st.session_state['file'] = update # 不能修改widget绑定的值
            st.query_params['file'] = update
            st.session_state['data_file'] = update
            state_df(update=read_file(update), save=False)  # 刚从磁盘读取的原始数据,无需save
            state_meta_df(update=True)  # 更新df同时也要更新meta_df
        elif 'data_file' not in st.session_state:
            st.session_state['data_file'] = None
        return st.session_state['data_file']


    def state_df(update: pd.DataFrame = None, save=True) -> pd.DataFrame:
        """
        :param update: 更新df, 来自数据操作/文件变更
        :param save: 写入磁盘
        :return: df缓存
        """
        if 'df' not in st.session_state:  # 初始化session
            st.session_state['df'] = None
        if update is not None:
            st.session_state['df'] = update  # 这行代码导致UI刷新,editor高度变化
            if save:
                write_file(data=update, file=state_data_file())
        if st.session_state['df'] is None:
            state_df(read_file(state_data_file()), save=False)  # 刚从磁盘读取的原始数据,无需save
            state_meta_df(update=True)  # 更新df同时也要更新meta_df
        return st.session_state['df']


    def state_meta_df(update: bool = False) -> pd.DataFrame:
        """
        :param update: 由于meta_df 直接来自于df, 没有持久化, 因此update用bool表达
        :return:
        """
        if 'meta_df' not in st.session_state:  # 初始化session
            st.session_state['meta_df'] = None
        if update or st.session_state['meta_df'] is None:
            meta_df = state_df().dtypes.astype(str).reset_index()
            meta_df.rename(columns={'index': 'col_name', 0: 'col_type'}, inplace=True)
            meta_df['col_name'] = meta_df['col_name'].astype(str)
            st.session_state['meta_df'] = meta_df
        return st.session_state['meta_df']


    def _on_change_file():
        if (file := st.session_state['file']) != state_data_file():  # 文件变更
            state_data_file(update=file)  # 更新文件路径


    def _on_change_edited_df():
        """state自带update用于更新状态, 本函数只用于接收editor的change,转换为state(update)"""
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
        state_df(df, save=True)  # 刷新 df


    def _on_change_edited_meta_df():
        """state自带update用于更新状态, 本函数只用于接收editor的change,转换为state(update)"""
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
        state_meta_df(update=True)  # 注意刷新 meta_df


    if 'file' in st.query_params:  # 从URL更新
        _file = st.query_params.get('file')
        state_data_file(update=_file)
        st.session_state['file'] = _file  # state_data_file不能修改widget绑定的值,因此在这里初始化
    if 'file' not in st.session_state:  # 初始化: 传入示例数据
        st.session_state['file'] = _DEFAULT_DATA_FILE

    """## TinyData"""
    with st.expander(f"数据源 {st.session_state.get('file') or ""}", expanded=st.query_params.get('file') is None):
        st.text_input("文件路径", key='file', on_change=_on_change_file)

    # st.session_state
    if st.session_state.get('df') is None:
        st.stop()  # 未打开文件则暂停

    with st.expander("编辑列", expanded=True):
        st.data_editor(
            state_meta_df(), key='edited_meta_df', use_container_width=True,
            height=adp_data_editor_height(len(state_meta_df())),
            on_change=_on_change_edited_meta_df, num_rows="dynamic",
            column_config={'col_name': st.column_config.TextColumn(label='列名', help='编辑列名称'),
                           'col_type': st.column_config.SelectboxColumn(label='类型', help='指定类型',
                                                                        options=['object', 'float64', 'int64'])}
        )

    with st.expander("编辑行", expanded=True):
        st.data_editor(
            state_df(), key='edited_df', use_container_width=True, height=adp_data_editor_height(len(state_df())),
            on_change=_on_change_edited_df, num_rows="dynamic",
            column_config={meta['col_name']: {'type_config': {  # 参见 class TextColumnConfig(TypedDict):
                'type': 'text' if (meta['col_type'] in ['object', 'str']) else 'number'}
            } for meta in state_meta_df().to_dict(orient='records')},
        )
