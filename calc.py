#pip install xlrd
#pip install openpyxl
import pandas as pd
import datetime

FILE_DIR = "E:\\code\\diaz-project\\resources"
FILE_NAME = "mybook.xlsx"
FILE_PATH = FILE_DIR + "\\" + FILE_NAME

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
from openpyxl import load_workbook

def write_df_to_excel(file_path = FILE_PATH, df = None, sheet_name = 'sheet'):
    book = load_workbook(file_path)
    writer = pd.ExcelWriter(file_path, engine='openpyxl') # pylint: disable=abstract-class-instantiated
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    df.to_excel(writer, sheet_name = sheet_name, index = False)
    writer.save()
    writer.close()

TIME_DIFF_SEC_COLUMN = 'TIME DIFF SEC'

def task1(file_path, input_sheet_name, output_sheet_name):
    df = pd.read_excel(file_path, sheet_name = input_sheet_name)
    print(df.head())

    previous_event_context = None
    end_time_index = None
    start_time_index = None
    DATE_TIME_FORMAT = '%m/%d/%y %H:%M:%S'
    DATE_TIME_COLUMN = 'Date/Time'
    
    TIME_DIFF_COLUMN_INDEX = 4
    ll = []

    #todo: replace iterrow with faster alternative
    for index, row in df.iterrows():
        if(row['Event context'] != previous_event_context):
            if(start_time_index != None) :
                start_time = datetime.datetime.strptime(df.at[start_time_index, DATE_TIME_COLUMN], DATE_TIME_FORMAT)
                end_time = datetime.datetime.strptime(df.at[end_time_index, DATE_TIME_COLUMN], DATE_TIME_FORMAT)
                #print("end_time_index = %r start_time_index = %r " % (end_time_index, start_time_index))
                #print("end_time = %r start_time = %r" % (end_time, start_time))
                diff_time = end_time - start_time
                active_row = df.iloc[start_time_index]
                active_row_as_list = active_row.values.tolist()
                active_row_as_list[TIME_DIFF_COLUMN_INDEX] = diff_time.seconds
                #print(active_row_as_list)
                ll.append(active_row_as_list)
                #print(diff_time.seconds)
            end_time_index = index
        start_time_index = index
        previous_event_context = row['Event context']

    df1 = pd.DataFrame(ll, columns = df.columns)
    write_df_to_excel(file_path = file_path, df = df1, sheet_name = output_sheet_name)

    print("step 1 done...")

def task2_and_3(file_path, input_sheet_name, output_sheet_name):
    df = pd.read_excel(file_path, sheet_name=input_sheet_name)
    zero_count = 0
    consecutive_zero_dict = dict()
    #total_consecutive_zero = 0
    #total_sec_assigned_to_consecutive_zero = 0
    df[TIME_DIFF_SEC_COLUMN] = df[TIME_DIFF_SEC_COLUMN].astype(float)
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
                    df.at[i, TIME_DIFF_SEC_COLUMN] = time_value
                    event_name = df.at[i, EVENT_CONTEXT_COLUMN]
                    if event_name in consecutive_zero_dict:
                        data = consecutive_zero_dict.get(event_name)
                        data[0] = data[0] + 1 #increment counter
                        data[1] = data[1] + time_value #update cumulative sum for that event
                    else:
                        consecutive_zero_dict[event_name] = [1, time_value]
            zero_count = 0

    #time_for_single_zero = float(total_sec_assigned_to_consecutive_zero) / total_consecutive_zero
    import numpy as np
    for key, value in consecutive_zero_dict.items():
        #print("Event = %r Count = %r CUMUL_TIME = %r" % (key, value[0], value[1]))
        df[TIME_DIFF_SEC_COLUMN] = np.where((df[TIME_DIFF_SEC_COLUMN] == 0.0) & (df[EVENT_CONTEXT_COLUMN] == key), value[1]/value[0], df[TIME_DIFF_SEC_COLUMN])
    #print(df[[TIME_DIFF_SEC_COLUMN]].head(19))
    write_df_to_excel(file_path, df, output_sheet_name)
    print("task 2-3 done...")
if __name__ == "__main__":
    #task1(FILE_PATH, input_sheet_name='Sheet1', output_sheet_name='Task1')
    task2_and_3(FILE_PATH, input_sheet_name='Task1', output_sheet_name = 'Task2-3')

    
    

