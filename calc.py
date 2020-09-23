#pip install xlrd
#pip install openpyxl
#pip install matplotlib
import pandas as pd
import datetime
import numpy as np
import os.path
import enum
from openpyxl import load_workbook

class ExcelColumnName(enum.Enum):
    DATE_TIME = 'Date/Time'
    TIME_DIFF_SEC = 'TIME DIFF SEC'
    USER_FULL_NAME = 'User full name'
    EVENT_CONTEXT = 'Event context'

class ExcelColumnIndex(enum.Enum):
    TIME_DIFF_SEC = 4

FILE_DIR = r'E:\code\student-data-project\resources'
OUTPUT_FILE_DIR = FILE_DIR
FILE_NAME = 'mybook.xlsx'
FILE_PATH = os.path.join(FILE_DIR, FILE_NAME)

'''
password = "1g2K47B"

import win32com.client
xlApp = win32com.client.Dispatch("Excel.Application")
xlwb = xlApp.Workbooks.Open(FILE_PATH, False, True, None, password)
sheet = xlwb.Worksheets("sheet1")
content = list(sheet.Range(sheet.Cells(1,1), sheet.Cells(sheet.UsedRange.Rows.Count, sheet.UsedRange.Columns.Count)).Value)
df = pd.DataFrame(content[1:], columns = content[0])
print(df.tail())
add = xlwb.Sheets.Add(Before = None, After = xlwb.Sheets(xlwb.Sheets.Count))
add.Name = "Summary"
xlwb.Save()
xlwb.Close()
xlApp.Quit()
'''
def write_df_to_excel(file_path = FILE_PATH, df = None, sheet_name = 'sheet', index_bool = False):
    book = load_workbook(file_path)
    writer = pd.ExcelWriter(file_path, engine='openpyxl') # pylint: disable=abstract-class-instantiated
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    df.to_excel(writer, sheet_name = sheet_name, index = index_bool)
    writer.save()
    writer.close()

def write_df_to_csv(file_path, df):
    df.to_csv(file_path, encoding = 'utf-8')

def task1(file_path, input_sheet_name, output_file_path):

    df = pd.read_excel(file_path, sheet_name = input_sheet_name)
    
    print(df.head())

    previous_event_context = None
    end_time_index = None
    start_time_index = None
    DATE_TIME_FORMAT = '%m/%d/%y %H:%M:%S'
    
    ll = []

    for index in df.index:
        if(df.at[index,ExcelColumnName.EVENT_CONTEXT.value] != previous_event_context):
            if(start_time_index != None) :
                start_time = datetime.datetime.strptime(df.at[start_time_index, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
                end_time = datetime.datetime.strptime(df.at[end_time_index, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
                #print("end_time_index = %r start_time_index = %r " % (end_time_index, start_time_index))
                #print("end_time = %r start_time = %r" % (end_time, start_time))
                if((start_time_index != end_time_index and start_time == end_time) and end_time_index - 1 >= 0): # consecutive events with same timestamp and next event exists
                    end_time = datetime.datetime.strptime(df.at[end_time_index - 1, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT) # end_time = next_event's start_time

                diff_time = end_time - start_time
                active_row = df.iloc[start_time_index]
                active_row_as_list = active_row.values.tolist()
                active_row_as_list[ExcelColumnIndex.TIME_DIFF_SEC.value] = diff_time.seconds
                ll.append(active_row_as_list)
            end_time_index = index
        start_time_index = index
        previous_event_context = df.at[index, ExcelColumnName.EVENT_CONTEXT.value]

    df1 = pd.DataFrame(ll, columns = df.columns)
    #write_df_to_excel(file_path = file_path, df = df1, sheet_name = output_sheet_name)
    write_df_to_csv(file_path = output_file_path, df = df1)
    print("task 1 done...")

def task2_and_3(file_path, input_sheet_name, output_sheet_name):
    df = pd.read_excel(file_path, sheet_name=input_sheet_name)
    zero_count = 0
    consecutive_zero_dict = dict()
    #total_consecutive_zero = 0
    #total_sec_assigned_to_consecutive_zero = 0
    df[ExcelColumnName.TIME_DIFF_SEC.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].astype(float)
    EVENT_CONTEXT_COLUMN = 'Event context'
    for index in df.index:
        if df.at[index, TIME_DIFF_SEC_COLUMN] == 0:
            zero_count = zero_count + 1
        else:
            if zero_count > 1:
                start_index = index - zero_count
                end_index = index - 1
                #print("start_index = %r end_index = %r" % (start_index, end_index))                
                time_value = 60.0 / zero_count
                #total_consecutive_zero = total_consecutive_zero + zero_count
                #total_sec_assigned_to_consecutive_zero = total_sec_assigned_to_consecutive_zero + 60
                for i in range(start_index, index):
                    df.at[i, ExcelColumnName.TIME_DIFF_SEC.value] = time_value
                    event_name = df.at[i, ExcelColumnName.EVENT_CONTEXT.value]
                    if event_name in consecutive_zero_dict:
                        data = consecutive_zero_dict.get(event_name)
                        data[0] = data[0] + 1 #increment counter
                        data[1] = data[1] + time_value #update cumulative sum for that event
                    else:
                        consecutive_zero_dict[event_name] = [1, time_value]
            zero_count = 0

    #time_for_single_zero = float(total_sec_assigned_to_consecutive_zero) / total_consecutive_zero
    for key, value in consecutive_zero_dict.items():
        #print("Event = %r Count = %r CUMUL_TIME = %r" % (key, value[0], value[1]))
        df[TIME_DIFF_SEC_COLUMN] = np.where((df[TIME_DIFF_SEC_COLUMN] == 0.0) & (df[EVENT_CONTEXT_COLUMN] == key), value[1]/value[0], df[TIME_DIFF_SEC_COLUMN])
    #print(df[[TIME_DIFF_SEC_COLUMN]].head(19))
    write_df_to_excel(file_path, df, output_sheet_name)
    print("task 2-3 done...")

#drop the first row of each students consecutive data. (Except the first row in the excel)
#ques: first row in the excel?
def task4(file_path, input_sheet_name, output_sheet_name):
    df = pd.read_excel(file_path, sheet_name=input_sheet_name)
    df.drop(df[(df[ExcelColumnName.USER_FULL_NAME.value] != df[ExcelColumnName.USER_FULL_NAME.value].shift(1)) & \
        (df[ExcelColumnName.USER_FULL_NAME.value].shift(1).apply(lambda x : isinstance(x,str)))].index, inplace = True)
    write_df_to_excel(file_path, df, output_sheet_name)
    print("task4 done...")

def get_cut_off_points(df, event_name):
    return np.percentile(df[df[ExcelColumnName.EVENT_CONTEXT.value] == event_name][ExcelColumnName.TIME_DIFF_SEC.value], [25,75], interpolation='midpoint')

def task5(file_path, input_sheet_name, output_sheet_name):
    df = pd.read_excel(file_path, sheet_name=input_sheet_name)
    EVENT_CONTEXT_COLUMN = ExcelColumnName.EVENT_CONTEXT.value
    TIME_DIFF_SEC_COLUMN = ExcelColumnName.TIME_DIFF_SEC.value
    event_list = sorted(df[EVENT_CONTEXT_COLUMN].unique())
    event_dict = dict()
    for event_name in event_list:
        event_dict[event_name] = df[df[EVENT_CONTEXT_COLUMN] == event_name][TIME_DIFF_SEC_COLUMN].describe()
    stat_df = pd.DataFrame.from_dict(event_dict, orient = 'index')
    stat_df = stat_df.rename_axis(None)
    stat_df.index.names = ['']
    write_df_to_excel(file_path, stat_df, input_sheet_name + "-stat", index_bool=True)
    print(len(df))
    """
    for event_name in event_list:
        df[df[EVENT_CONTEXT_COLUMN] == event_name][TIME_DIFF_SEC_COLUMN].hist()
        if cnt:
            break
    """
    for event_name in event_list:
        cut_off_points = get_cut_off_points(df, event_name)
        df.drop(df[(df[EVENT_CONTEXT_COLUMN] == event_name) & \
            ((df[TIME_DIFF_SEC_COLUMN] < cut_off_points[0]) | (df[TIME_DIFF_SEC_COLUMN] > cut_off_points[1]))].index, \
                inplace = True)
    print(len(df))
    print("task 5 done")

if __name__ == "__main__":
    task1(FILE_PATH, input_sheet_name='Sheet1', output_file_path = os.path.join(OUTPUT_FILE_DIR, 'Task1.csv'))
    #task2_and_3(FILE_PATH, input_sheet_name='Task1', output_sheet_name = 'Task2-3')
    #task4(FILE_PATH, input_sheet_name='Task2-3', output_sheet_name='Task4')
    #task5(FILE_PATH, input_sheet_name='Task4', output_sheet_name=None)