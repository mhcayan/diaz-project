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
    EVENT_CONTEXT = 'Event Context'
    IS_SINGLE_EVENT = 'is_single_event'
    MAD = 'MAD'
    MEAN_AD = 'MeanAD'

class ExcelColumnIndex(enum.Enum):
    TIME_DIFF_SEC = 4
    EVENT_CONTEXT = 9

class ThresholdType(enum.Enum):
    TEN_MINUTES = 0
    THIRTY_MINUTES = 5
    INTERQUARTILE_RANGE = 10
    MODIFIED_Z_SCORE = 15 

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FILE_DIR = r'F:\E\code\student-data-project\resources'
OUTPUT_FILE_DIR = FILE_DIR
FILE_NAME = 'test.xlsx'
FILE_PATH = os.path.join(FILE_DIR, FILE_NAME)

THIRTY_MINUTES_IN_SEC = 30 * 60
TEN_MINUTES_IN_SEC = 10 * 60

DEFAULT_EXAM_DURATION = TEN_MINUTES_IN_SEC

SINGLE_EVENTS_PREFIX = '$single-event$ - '
QUIZ_EVENTS_PREFIX = 'quiz'

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
    start_time = df.at[start_time_index, ExcelColumnName.DATE_TIME.value] 
    end_time = df.at[end_time_index, ExcelColumnName.DATE_TIME.value]
    start_time = datetime.datetime.strptime(start_time, DATE_TIME_FORMAT)
    end_time = datetime.datetime.strptime(end_time, DATE_TIME_FORMAT)
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

def delete_invalid_users(input_file_path, input_sheet_name, output_file_path):

    df = pd.read_excel(input_file_path, sheet_name = input_sheet_name)
    df[ExcelColumnName.EVENT_CONTEXT.value] = df[ExcelColumnName.EVENT_CONTEXT.value].str.lower() #change all event name to lower case
    invalid_users = ["A", "B", "C", "D", "E", "9"]
    df = df[~df["User full name"].isin(invalid_users)]
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)

#change all event name to lower case
#for each event, compute it's duration (end_time-start_time)
#add a new column to represent Event_duration in HH:MM:SS
def compute_event_duration(input_file_path, input_sheet_name, output_file_path):

    df = pd.read_csv(input_file_path)
    
    #df[ExcelColumnName.DATE_TIME.value] = df[ExcelColumnName.DATE_TIME.value].astype('str')
    
    df.reset_index(drop = True, inplace = True)

    df.insert(5, ExcelColumnName.TIME_DIFF_HH_MM_SS.value, "") #add a new column to represent event duration in hh:mm:ss

    print("Task: compute event duration started..")

    end_time_index = 0
    start_time_index = None
    computed_row_list = []
    #for the first event the duration will be 0. (We don't know it's end time.)
    try:
        for index in df.index:
            if index % 10000 == 0:
                print("%r record processed.." % index)
            start_time_index = index
            compute_diff_time_sec_new(df, start_time_index, end_time_index, computed_row_list)
            end_time_index = start_time_index
    except Exception as e:
        print("error!! start_index = %r end_index = %r" % (start_time_index, end_time_index))
        print(e)
        
    df = pd.DataFrame(computed_row_list, columns = df.columns)
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)
    print("Task: compute event duration finished..")
    print("\n----------------------------------------\n")

#drop the first row(last event) of each students data.
#assumption: A students all records are in consecutive order (all in in one place in the spreadsheet).  
def delete_students_last_event(input_file_path, output_file_path):
    df = pd.read_csv(input_file_path)
    print("Task: delete students last event started..")
    df[ExcelColumnName.USER_FULL_NAME.value] = df[ExcelColumnName.USER_FULL_NAME.value].astype(str)
    df.drop(df[df[ExcelColumnName.USER_FULL_NAME.value] != df[ExcelColumnName.USER_FULL_NAME.value].shift(1)].index, inplace = True)
    write_df_to_csv(output_file_path, df)
    print("Task: delete students last event finished..")
    print("\n----------------------------------------\n")

#delete events having zero duration(TIME_DIFF_SEC = 0)
def delete_zero_duration_event(input_file_path, output_file_path):

    print("Task: delete zero duration event started..")
    df = pd.read_csv(input_file_path)
    initial_length = len(df)
    df = df[df[ExcelColumnName.TIME_DIFF_SEC.value] != 0]
    print("%r records deleted.." % (initial_length - len(df)))
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)
    print("Task: delete zero duration event finished..")
    print("\n----------------------------------------\n")

#events whose name startswith "quiz: exam" or "quiz: final exam", set its first occurance with 0 time in a series of events. (both for single and consecutive)
def reset_last_quiz_events_duration(input_file_path, output_file_path):
    print("Task: reset last quiz event's duration started..")
    df = pd.read_csv(input_file_path)

    lastStudent = None
    lastEvent = None
    for index in df.index:
        student = df.at[index, ExcelColumnName.USER_FULL_NAME.value]
        event = df.at[index, ExcelColumnName.EVENT_CONTEXT.value]
        if event.startswith("quiz: exam") | event.startswith("quiz: final exam"):
            if (student != lastStudent) | (event != lastEvent):
                df.at[index, ExcelColumnName.TIME_DIFF_SEC.value] = 0
        lastStudent = student
        lastEvent = event
    
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)
    print("Task: reset last quiz event's duration finished..")
    print("\n----------------------------------------\n")

#for events which have negative time assume they were ended in the next year
#talk: deleting events with 0 duration?
def fix_negative_time(input_file_path, output_file_path):

    print("Task: fix negative time started..")
    
    df = pd.read_csv(input_file_path)
    initial_length = len(df)
    df = df[df[ExcelColumnName.TIME_DIFF_SEC.value] >= 0]
    print("%r records deleted.." % (initial_length - len(df)))
    write_df_to_csv(output_file_path, df = df)
    print("Task: fix negative time finished..")
    print("\n----------------------------------------\n")
    
#generate statistics(mean, median...) for each event
def generate_statistics(input_file_path, output_file_path, remove_event_prefix = False):

    print("Task: generate statistics started..")
    df = pd.read_csv(input_file_path)
    EVENT_CONTEXT_COLUMN = ExcelColumnName.EVENT_CONTEXT.value
    TIME_DIFF_SEC_COLUMN = ExcelColumnName.TIME_DIFF_SEC.value

    if remove_event_prefix:
        df[EVENT_CONTEXT_COLUMN] = df[EVENT_CONTEXT_COLUMN].apply(lambda event_name : remove_prefix(event_name, SINGLE_EVENTS_PREFIX))

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

def remove_prefix(s, prefix):
    return s[len(prefix):] if s.startswith(prefix) else s

#private function used by "fix_long_events_duration" to fix 
def fix_outlier_by_single_threshold(row, stat_df, threshold):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    if time_diff_sec > threshold:
        event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
        if event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam'):
            return DEFAULT_EXAM_DURATION
        else:
            return stat_df.at[event_context, "50%"]
    return time_diff_sec

#private function used by "fix_long_events_duration" to fix
#only updates the duration of the single events 
def fix_single_event_outlier_by_single_threshold(row, stat_df, threshold):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    is_single_event = row[ExcelColumnName.IS_SINGLE_EVENT.value]
    if is_single_event and (time_diff_sec > threshold):
        event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
        if event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam'):
            return DEFAULT_EXAM_DURATION
        else:
            return stat_df.at[event_context, "50%"]
    return time_diff_sec

def update_duration(row, left_threshold, right_threshold, left_outlier_replacement_val, right_outlier_replacement_val):
    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    if time_diff_sec < left_threshold:
        return left_outlier_replacement_val
    if time_diff_sec > right_threshold:
        return right_outlier_replacement_val
    return time_diff_sec

def update_duration_by_interquartile_range(row, stat_df):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    interquartile_range = stat_df.at[event_context, "75%"] - stat_df.at[event_context, "25%"] 
    left_threshold = -1.5 * interquartile_range
    right_threshold = 1.5 * interquartile_range
    return update_duration(row, left_threshold = left_threshold, 
                                right_threshold = right_threshold, 
                                left_outlier_replacement_val = left_threshold,
                                right_outlier_replacement_val= right_threshold)

def update_single_events_duration_by_interquartile_range(row, stat_df):
    is_single_event = row[ExcelColumnName.IS_SINGLE_EVENT.value]
    if is_single_event:
        return update_duration_by_interquartile_range(row, stat_df)
    else:
        return row[ExcelColumnName.TIME_DIFF_SEC.value]



def update_duration_by_modified_z_score(row, stat_df):
    
    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    mad = stat_df.at[event_context, ExcelColumnName.MAD.value]
    meanAD = stat_df.at[event_context, ExcelColumnName.MEAN_AD.value]

    #talk:
    if mad == 0 and meanAD == 0:
        return time_diff_sec

    median = stat_df.at[event_context, '50%']
    left_threshold = -3.5
    right_threshold = 3.5
    
    #https://www.ibm.com/docs/en/cognos-analytics/11.1.0?topic=terms-modified-z-score
    if mad == 0:
        CONSTANT_FACTOR = 1.253314
        modified_z_score = (time_diff_sec-median) / (CONSTANT_FACTOR * meanAD)
        left_outlier_replacement_value = left_threshold * CONSTANT_FACTOR * meanAD + median
        right_outlier_replacement_value = right_threshold * CONSTANT_FACTOR * meanAD + median
    else:
        CONSTANT_FACTOR = 1.486
        modified_z_score = (time_diff_sec-median)/(CONSTANT_FACTOR * mad)
        left_outlier_replacement_value = left_threshold * CONSTANT_FACTOR * mad + median
        right_outlier_replacement_value = right_threshold * CONSTANT_FACTOR * mad + median
    

    return update_duration(row, left_threshold = left_threshold, 
                                right_threshold = right_threshold, 
                                left_outlier_replacement_val = left_outlier_replacement_value,
                                right_outlier_replacement_val= right_outlier_replacement_value)


def update_single_events_duration_by_modified_z_score(row, stat_df):
    is_single_event = row[ExcelColumnName.IS_SINGLE_EVENT.value]
    if is_single_event:
        return update_duration_by_modified_z_score(row, stat_df)
    else:
        return row[ExcelColumnName.TIME_DIFF_SEC.value]

def mark_single_events(input_file_path, output_file_path):
    
    print("Task: mark single events started..")
    df = pd.read_csv(input_file_path)

    #mark single events
    df[ExcelColumnName.IS_SINGLE_EVENT.value] = False
    count = 0
    for index in df.index:
        if index == 0:
            count = 1
        else:
            if (df.at[index, ExcelColumnName.USER_FULL_NAME.value] != df.at[index - 1, ExcelColumnName.USER_FULL_NAME.value]) or (df.at[index, ExcelColumnName.EVENT_CONTEXT.value] != df.at[index - 1, ExcelColumnName.EVENT_CONTEXT.value]):
                if count == 1:
                    df.at[index - 1, ExcelColumnName.IS_SINGLE_EVENT.value] = True
                count = 1
            else:
                count = count + 1
    write_df_to_csv(output_file_path, df)
    print("Task: mark single events started..")

def compute_MAD(s):
    median_s = s.median()
    return (abs(s-median_s)).median()

def compute_MeanAD(s):
    median_s = s.median()
    return (abs(s - median_s)).mean()


#fix events' TIME_DIFF_SEC, when it's duration is more than 30 minutes. For events with prefix "quiz: exam" and "quiz: final exam" update duration to 30 minutes, 
# for other events update their durtion with the median duration of that event
#param by: 
#param all_events: true -> update all events, false -> update only single events and the last events of each student
#
def fix_outliers(input_file_path, output_file_path, stat_file_path, by, all_events):

    print("Task: fix long events' duration started..")
    df = pd.read_csv(input_file_path)
    stat_df = pd.read_csv(stat_file_path)
    stat_df.set_index('Unnamed: 0', inplace = True)

    if by == ThresholdType.TEN_MINUTES:
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_outlier_by_single_threshold(row, stat_df, threshold=TEN_MINUTES_IN_SEC), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_single_event_outlier_by_single_threshold(row, stat_df, threshold=TEN_MINUTES_IN_SEC), axis = 1)
    elif by == ThresholdType.THIRTY_MINUTES:
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_outlier_by_single_threshold(row, stat_df, threshold=THIRTY_MINUTES_IN_SEC), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_single_event_outlier_by_single_threshold(row, stat_df, threshold=THIRTY_MINUTES_IN_SEC), axis = 1)

    elif by == ThresholdType.INTERQUARTILE_RANGE:
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_duration_by_interquartile_range(row, stat_df), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_single_events_duration_by_interquartile_range(row, stat_df), axis = 1)
   
    elif by == ThresholdType.MODIFIED_Z_SCORE:
       #compute MAD for each event_context
        stat_df['MAD'] = stat_df.apply(lambda row : compute_MAD(df[df[ExcelColumnName.EVENT_CONTEXT.value] == row.name][ExcelColumnName.TIME_DIFF_SEC.value]), axis = 1)
        stat_df['MeanAD'] = stat_df.apply(lambda row : compute_MeanAD(df[df[ExcelColumnName.EVENT_CONTEXT.value] == row.name][ExcelColumnName.TIME_DIFF_SEC.value]), axis = 1)
        write_df_to_csv(os.path.join(OUTPUT_FILE_DIR, 'updated_stat_df.csv'), stat_df)
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_duration_by_modified_z_score(row, stat_df), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_single_events_duration_by_modified_z_score(row, stat_df), axis = 1)

    else:
        raise Exception("Invalid value for param 'by'")

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
        active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value] = SINGLE_EVENTS_PREFIX + active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value]
    computed_row_list.append(active_row_as_list)
    df = pd.DataFrame(computed_row_list, columns = df.columns)
    df[ExcelColumnName.TIME_DIFF_HH_MM_SS.value] = df[ExcelColumnName.TIME_DIFF_SEC.value].map(sec_to_hh_mm_ss)
    write_df_to_csv(output_file_path, df)
    print("Task: aggregate events finished..")
    print("\n----------------------------------------\n")

def delete_single_quiz_events(input_file_path, output_file_path):
    df = pd.read_csv(input_file_path)
    df = df[~df[ExcelColumnName.EVENT_CONTEXT.value].str.startswith(SINGLE_EVENTS_PREFIX + QUIZ_EVENTS_PREFIX)]
    write_df_to_csv(output_file_path, df)

#if there are multiple instances of same quiz events for a student, then keep the one with maximum duration
def delete_duplicate_quiz_events(input_file_path, output_file_path):
    df = pd.read_csv(input_file_path)
    data_dict = dict()
    for index in df.index:
        event_name = df.iloc[index][ExcelColumnName.EVENT_CONTEXT.value]
        if event_name.startswith(QUIZ_EVENTS_PREFIX):
            event_duration = df.iloc[index][ExcelColumnName.TIME_DIFF_SEC.value]
            user_name = df.iloc[index][ExcelColumnName.USER_FULL_NAME.value]
            if user_name not in data_dict:
                data_dict[user_name] = dict()
            event_dict = data_dict[user_name]
            max_duration = event_dict.get(event_name, None)
            if not max_duration or max_duration < event_duration:
                event_dict[event_name] = event_duration
    #print(data_dict)
    
    filtered_rows = []
    for index in df.index:
        event_name = df.iloc[index][ExcelColumnName.EVENT_CONTEXT.value]
        if event_name.startswith(QUIZ_EVENTS_PREFIX): #if it's a quiz event
            user_name = df.iloc[index][ExcelColumnName.USER_FULL_NAME.value]
            user_event_dict = data_dict[user_name]
            if event_name in user_event_dict:
                max_duration = user_event_dict.get(event_name)
                event_duration = df.iloc[index][ExcelColumnName.TIME_DIFF_SEC.value]
                if event_duration == max_duration:
                    filtered_rows.append(df.iloc[index].values.tolist())
                    del user_event_dict[event_name]
        else:
            filtered_rows.append(df.iloc[index].values.tolist())
    df = pd.DataFrame(filtered_rows, columns = df.columns)
    write_df_to_csv(output_file_path, df)


    



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

def check_single_events(input_file_path):
    df = pd.read_csv(input_file_path)
    data_dict = dict()
    for index in df.index:
        event_name = df.iloc[index][ExcelColumnName.EVENT_CONTEXT.value]
        if event_name.startswith('quiz: exam') or event_name.startswith('quiz: final') or event_name.startswith('quiz: quiz'):
            user_name = df.iloc[index][ExcelColumnName.USER_FULL_NAME.value]
            if user_name not in data_dict:
                data_dict[user_name] = dict()
            event_dict = data_dict[user_name]
            event_cnt = event_dict.get(event_name, 0)
            event_dict[event_name] = event_cnt + 1
    #print(data_dict)
    for user_name, event_dict in data_dict.items():
        for event_name, event_count in event_dict.items():
            if event_count < 2:
                print("%r %r\n" % (user_name, event_name))


if __name__ == "__main__":

    deleted_invalid_users_output_file_name = "0_invalid_users_deleted.csv"
    event_duration_output_file_name = '1_event_duration.csv'
    students_last_event_deleted_file_name = '2_students_last_event_deleted.csv'
    negative_time_fixed_file_name = "3_negative_time_fixed.csv"
    zero_duration_event_deleted_file_name = "4_zero_duration_event_deleted.csv"
    reset_last_quiz_events_duration_file_name = "5_reset_last_quiz_events_duration.csv"
    statistics_output_file_name = '6_statistics.csv'
    marked_single_events_file_name = "6a_marked_singled_events.csv"
    
    outlier_fixed_by_10_min_all_event_output_file_name = '6a_outlier_fixed_by_10min_threshold_all_event.csv'
    outlier_fixed_by_10_min_single_only_output_file_name = '6b_outlier_fixed_by_10min_threshold_single_only.csv'
    outlier_fixed_by_30_min_all_event_output_file_name = '6c_outlier_fixed_by_30min_threshold_all_event.csv'
    outlier_fixed_by_30_min_single_only_output_file_name = '6d_outlier_fixed_by_30min_threshold_single_only.csv'
    outlier_fixed_by_iqr_all_event_output_file_name = '6e_outlier_fixed_by_iqr_all_event.csv'
    outlier_fixed_by_iqr_single_only_output_file_name = '6f_outlier_fixed_by_iqr_single_only.csv'
    outlier_fixed_by_modz_all_event_output_file_name = '6g_outlier_fixed_by_mod_z_score_all_event.csv'
    outlier_fixed_by_modz_single_only_output_file_name = '6h_outlier_fixed_by_mod_z_score_single_only.csv'
    
    aggregated_events_output_file_name = "7_aggregated_events.csv"
    single_quiz_events_deleted_file_name = "8_single_quiz_events_deleted.csv"
    duplicate_quiz_events_deleted_file_name = "9_duplicate_quiz_events_deleted.csv"
    aggregated_events_statistics_file_name = "10_aggregated_events_statistics.csv"
    
    
    #check_single_events(os.path.join(OUTPUT_FILE_DIR, '4_zero_duration_event_deleted.csv'))
    # delete_invalid_users(FILE_PATH, input_sheet_name='Sheet1', 
    #                     output_file_path = os.path.join(OUTPUT_FILE_DIR, deleted_invalid_users_output_file_name))
    # compute_event_duration(os.path.join(OUTPUT_FILE_DIR, deleted_invalid_users_output_file_name),
    #                     input_sheet_name='Sheet1', output_file_path = os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name))
    # delete_students_last_event(os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name), 
    #                     output_file_path = os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name))
    # fix_negative_time(os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name))
    # delete_zero_duration_event(os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name))
    reset_last_quiz_events_duration(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), 
                        os.path.join(OUTPUT_FILE_DIR, reset_last_quiz_events_duration_file_name))
    
    # generate_statistics(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name))
    # #mark_single_events(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name))

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_10_min_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.TEN_MINUTES, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_10_min_single_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.TEN_MINUTES, 
    #                         all_events = False)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_30_min_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.THIRTY_MINUTES, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_30_min_single_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.THIRTY_MINUTES, 
    #                         all_events = False)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_iqr_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.INTERQUARTILE_RANGE, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_iqr_single_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.INTERQUARTILE_RANGE, 
    #                         all_events = False)


    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_modz_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.MODIFIED_Z_SCORE, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_single_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_modz_single_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.MODIFIED_Z_SCORE, 
    #                         all_events = False)
    #aggregate_events(os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_10_min_all_event_output_file_name), os.path.join(OUTPUT_FILE_DIR, aggregated_events_output_file_name))
    #delete_single_quiz_events(os.path.join(OUTPUT_FILE_DIR, aggregated_events_output_file_name), os.path.join(OUTPUT_FILE_DIR, single_quiz_events_deleted_file_name))
    #delete_duplicate_quiz_events(os.path.join(OUTPUT_FILE_DIR, single_quiz_events_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, duplicate_quiz_events_deleted_file_name))
    #generate_statistics(os.path.join(OUTPUT_FILE_DIR, duplicate_quiz_events_deleted_file_name), os.path.join(OUTPUT_FILE_DIR, aggregated_events_statistics_file_name), remove_event_prefix = True)

