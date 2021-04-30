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
    TIME_DIFF_HH_MM_SS = 'TIME DIFF HH:MM:SS'
    USER_FULL_NAME = 'User full name'
    EVENT_CONTEXT = 'Event context'

class ExcelColumnIndex(enum.Enum):
    TIME_DIFF_SEC = 4
    EVENT_CONTEXT = 9

DATE_TIME_FORMAT = '%m/%d/%y %H:%M:%S'
FILE_DIR = r'F:\pc-backup\E\code\student-data-project\resources'
OUTPUT_FILE_DIR = FILE_DIR
FILE_NAME = 'mybook.xlsx'
FILE_PATH = os.path.join(FILE_DIR, FILE_NAME)

THIRTY_MINUTES_IN_SEC = 30 * 60

DEFAULT_EXAM_DURATION = THIRTY_MINUTES_IN_SEC

def write_df_to_excel(file_path = FILE_PATH, df = None, sheet_name = 'sheet', index_bool = False):
    book = load_workbook(file_path)
    writer = pd.ExcelWriter(file_path, engine='openpyxl') # pylint: disable=abstract-class-instantiated
    writer.book = book
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    df.to_excel(writer, sheet_name = sheet_name, index = index_bool)
    writer.save()
    writer.close()

def write_df_to_csv(file_path, df, index = False):
    df.to_csv(file_path, index = index, encoding = 'utf-8')

#since 3/12/2021
def get_time_diff(df, start_time_index, end_time_index):
    start_time = datetime.datetime.strptime(df.at[start_time_index, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
    end_time = datetime.datetime.strptime(df.at[end_time_index, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
    return end_time - start_time

#since: 3/9/2021
def compute_diff_time_sec_new(df, start_time_index, end_time_index, computed_row_list):

    active_row = df.iloc[start_time_index]
    active_row_as_list = active_row.values.tolist()
    active_row_as_list[ExcelColumnIndex.TIME_DIFF_SEC.value] = int(get_time_diff(df, start_time_index, end_time_index).total_seconds())
    computed_row_list.append(active_row_as_list)

def sec_to_hh_mm_ss(sec):
    if pd.isnull(sec):
        return sec
    if sec < 0:
        return sec
    return str(datetime.timedelta(seconds=sec))

#for each event, compute it's duration (end_time-start_time)
#add a new column to represent Event_duration in HH:MM:SS
def compute_event_duration(file_path, input_sheet_name, output_file_path):

    df = pd.read_excel(file_path, sheet_name = input_sheet_name)
    
    df[ExcelColumnName.EVENT_CONTEXT.value] = df[ExcelColumnName.EVENT_CONTEXT.value].str.lower() #change all event name to lower case

    #remove user A, B, C,D, E
    df = df[~df["User full name"].isin(["A", "B", "C", "D", "E"])]
    df.reset_index(drop = True, inplace = True)

    df.insert(5, ExcelColumnName.TIME_DIFF_HH_MM_SS.value, "") #add a new column to represent event duration in hh:mm:ss

    print("Task: compute event duration started..")

    end_time_index = None
    start_time_index = None
    computed_row_list = []
    try:
        for index in df.index:
            if index % 10000 == 0:
                print("%r record processed.." % index)
            start_time_index = index
            if end_time_index != None:
                compute_diff_time_sec_new(df, start_time_index, end_time_index, computed_row_list)
            end_time_index = start_time_index
    except:
        print("error!! start_index = %r end_index = %r" % (start_time_index, end_time_index))
        
    df = pd.DataFrame(computed_row_list, columns = df.columns)
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)
    print("Task: compute event duration finished..")
    print("\n----------------------------------------\n")

#drop the first row of each students data. (Except the first row in the excel)
def delete_students_last_event(input_file_path, output_file_path):
    df = pd.read_csv(input_file_path)
    print("Task: delete students last event started..")
    df.drop(df[(df[ExcelColumnName.USER_FULL_NAME.value] != df[ExcelColumnName.USER_FULL_NAME.value].shift(1)) & \
        (df[ExcelColumnName.USER_FULL_NAME.value].shift(1).apply(lambda x : isinstance(x,str)))].index, inplace = True)
    write_df_to_csv(output_file_path, df)
    print("Task: delete students last event finished..")
    print("\n----------------------------------------\n")

#delete events having zero duration(TIME_DIFF_SEC = 0)
def delete_zero_duration_event(input_file_path, output_file_path):

    print("Task: delete zero duration event started..")
    df = pd.read_csv(input_file_path)
    df = df[df[ExcelColumnName.TIME_DIFF_SEC.value] != 0]
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)
    print("Task: delete zero duration event finished..")
    print("\n----------------------------------------\n")

#for events which have negative time assume they were ended in the next year
def fix_negative_time(input_file_path, output_file_path):

    print("Task: fix negative time started..")
    df = pd.read_csv(input_file_path)
    for index in df.index:
        if index > 0 and df.at[index, ExcelColumnName.TIME_DIFF_SEC.value] < 0:
            start_time = datetime.datetime.strptime(df.at[index, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
            end_time = datetime.datetime.strptime(df.at[index - 1, ExcelColumnName.DATE_TIME.value], DATE_TIME_FORMAT)
            end_time = end_time.replace(year = end_time.year + 1) #assume the event was ended in the next year (increment end year)
            df.at[index, ExcelColumnName.TIME_DIFF_SEC.value] = int((end_time - start_time).total_seconds())

    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(output_file_path, df = df)
    print("Task: fix negative time finished..")
    print("\n----------------------------------------\n")

#generate statistics(mean, median...) from each event
def generate_statistics(input_file_path, output_file_path):

    print("Task: generate statistics started..")
    df = pd.read_csv(input_file_path)
    EVENT_CONTEXT_COLUMN = ExcelColumnName.EVENT_CONTEXT.value
    TIME_DIFF_SEC_COLUMN = ExcelColumnName.TIME_DIFF_SEC.value
    event_list = sorted(df[EVENT_CONTEXT_COLUMN].unique())
    event_dict = dict()
    for event_name in event_list:
        event_dict[event_name] = df[df[EVENT_CONTEXT_COLUMN] == event_name][TIME_DIFF_SEC_COLUMN].describe()
    stat_df = pd.DataFrame.from_dict(event_dict, orient = 'index')
    #stat_df = stat_df.rename_axis(None)
    #stat_df.index.names = ['']
    write_df_to_csv(output_file_path, stat_df, index = True)
    print("Task: generate statistics finished..")
    print("\n----------------------------------------\n")

#private function used by "fix_long_events_duration" to fix 
def update_duration(row, stat_df):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    if time_diff_sec > THIRTY_MINUTES_IN_SEC:
        event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
        if event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam'):
            return DEFAULT_EXAM_DURATION
        else:
            return stat_df.at[event_context, "50%"]
    return time_diff_sec

#fix events' TIME_DIFF_SEC, when it's duration is more than 30 minutes. For events with prefix "quiz: exam" and "quiz: final exam" update duration to 30 minutes, 
# for other events update their durtion with the median duration of that event
def fix_long_events_duration(input_file_path, output_file_path, stat_file_path):

    print("Task: fix long events' duration started..")
    df = pd.read_csv(input_file_path)
    stat_df = pd.read_csv(stat_file_path)
    stat_df.set_index('Unnamed: 0', inplace = True)
    df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda  row : update_duration(row, stat_df), axis = 1)
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(output_file_path, df)
    print("Task: fix long events' duration finished..")
    print("\n----------------------------------------\n")

#aggregate consecutive events(events with same event_context and full_user_name)
def aggregate_events(input_file_path, output_file_path):
    print("Task: aggregate events started..")
    df = pd.read_csv(input_file_path)
    computed_row_list = []
    cumulative_duration = 0
    event_count = 0
    for index in df.index:
        if index == 0:
            cumulative_duration = df.at[index, ExcelColumnName.TIME_DIFF_SEC.value]
            event_count = 1
        else:
            if index % 10000 == 0:
                print("%r record processed\n" % index)
            if (df.at[index, ExcelColumnName.USER_FULL_NAME.value] != df.at[index - 1, ExcelColumnName.USER_FULL_NAME.value]) or (df.at[index, ExcelColumnName.EVENT_CONTEXT.value] != df.at[index - 1, ExcelColumnName.EVENT_CONTEXT.value]):
                active_row = df.iloc[index - 1]
                active_row_as_list = active_row.values.tolist()
                active_row_as_list[ExcelColumnIndex.TIME_DIFF_SEC.value] = cumulative_duration
                if event_count == 1:
                    active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value] = '$single-event$ - ' + active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value]
                computed_row_list.append(active_row_as_list)
                cumulative_duration = df.at[index, ExcelColumnName.TIME_DIFF_SEC.value]
                event_count = 1
            else:
                cumulative_duration += df.at[index, ExcelColumnName.TIME_DIFF_SEC.value]
                event_count += 1

    active_row = df.iloc[len(df) - 1]
    active_row_as_list = active_row.values.tolist()
    active_row_as_list[ExcelColumnIndex.TIME_DIFF_SEC.value] = cumulative_duration
    if event_count == 1:
        active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value] = '$single-event$ - ' + active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value]
    computed_row_list.append(active_row_as_list)
    df = pd.DataFrame(computed_row_list, columns = df.columns)
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(output_file_path, df)
    print("Task: aggregate events finished..")
    print("\n----------------------------------------\n")

#obsolete
def task2(input_file_path, output_file_path):
    df = pd.read_csv(input_file_path)
    zero_count = 0
    consecutive_zero_event_dict = dict()
    #total_consecutive_zero = 0
    #total_sec_assigned_to_consecutive_zero = 0
    df[ExcelColumnName.TIME_DIFF_SEC.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].astype(float) #change datatype of column TIME_DIFF_SEC
    for index in df.index:
        
        if df.at[index, ExcelColumnName.TIME_DIFF_SEC.value] == 0 and \
            (zero_count == 0 or \
                (df.at[index-1, ExcelColumnName.TIME_DIFF_SEC.value] == 0 and df.at[index, ExcelColumnName.DATE_TIME.value] == df.at[index - 1, ExcelColumnName.DATE_TIME.value])):
            zero_count = zero_count + 1
        else:
            if zero_count > 1:
                start_index = index - zero_count
                end_index = index - 1
                #print("start_index = %r end_index = %r" % (start_index, end_index))                
                time_value = 60.0 / zero_count #time to be assigned to the consecutive zero events
                #total_consecutive_zero = total_consecutive_zero + zero_count
                #total_sec_assigned_to_consecutive_zero = total_sec_assigned_to_consecutive_zero + 60

                #assign all those consecutive zero events the calculated time value
                for i in range(start_index, index):
                    df.at[i, ExcelColumnName.TIME_DIFF_SEC.value] = time_value
                    event_name = df.at[i, ExcelColumnName.EVENT_CONTEXT.value]
                    if event_name in consecutive_zero_event_dict:
                        data = consecutive_zero_event_dict.get(event_name)
                        data[0] = data[0] + 1 #increment counter
                        data[1] = data[1] + time_value #update cumulative sum for that event
                    else:
                        consecutive_zero_event_dict[event_name] = [1, time_value]
            if df.at[index, ExcelColumnName.TIME_DIFF_SEC.value] == 0:
                zero_count = 1
            else:
                zero_count = 0
    write_df_to_csv(output_file_path, df)
    print("task 2 done...")
    return consecutive_zero_event_dict

#obsolete
def task3(input_file_path, output_file_path, consecutive_zero_event_dict):
    df = pd.read_csv(input_file_path)
    #time_for_single_zero = float(total_sec_assigned_to_consecutive_zero) / total_consecutive_zero
    for key, value in consecutive_zero_event_dict.items():
        #print("event = %40s freq = %3d sum = %3.5f" % (key[:min(30, len(key))], value[0], value[1]))
        df[ExcelColumnName.TIME_DIFF_SEC.value] = np.where((df[ExcelColumnName.TIME_DIFF_SEC.value] == 0.0) \
        & (df[ExcelColumnName.EVENT_CONTEXT.value] == key), value[1]/value[0], df[ExcelColumnName.TIME_DIFF_SEC.value])
    write_df_to_csv(output_file_path, df)
    print('task 3 done..')

if __name__ == "__main__":

    event_duration_output_file_name = '1_event_duration.csv'
    negative_time_fixed_file_name = "2_negative_time_fixed.csv"
    students_last_event_deleted_file_name = '3_students_last_event_deleted.csv'
    zero_duration_event_deleted_file_name = "4_zero_duration_event_deleted.csv"
    statistics_output_file_name = '5_statistics.csv'
    long_events_duration_fixed_output_file_name = '6_long_events_duration_fixed.csv'
    aggregated_events_output_file_name = "7_aggregated_events.csv"

    compute_event_duration(FILE_PATH, input_sheet_name='Sheet1', output_file_path = os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name))
    fix_negative_time(os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name), os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name))
    delete_students_last_event(os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name), output_file_path = os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name))
    delete_zero_duration_event(os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name))
    generate_statistics(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name))
    fix_long_events_duration(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, long_events_duration_fixed_output_file_name), os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name))
    aggregate_events(os.path.join(OUTPUT_FILE_DIR, long_events_duration_fixed_output_file_name), os.path.join(OUTPUT_FILE_DIR, aggregated_events_output_file_name))