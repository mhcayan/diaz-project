#pip install xlrd
#pip install openpyxl
#pip install matplotlib
from tkinter import SINGLE
import pandas as pd
import datetime
import numpy as np
import os.path
import enum
from openpyxl import load_workbook
import re

class ExcelColumnName(enum.Enum):

    FORMATTED_TIME = "formatted_time"
    TIME_DIFF_SEC = 'TIME DIFF SEC'
    TIME_DIFF_HH_MM_SS = 'TIME DIFF HH:MM:SS'
    USER_FULL_NAME = 'User full name'
    EVENT_CONTEXT = 'Event Context'
    IS_LAST_EVENT = 'is_last_event'
    MEDIAN_AD = 'MedianAD'
    MEAN_AD = 'MeanAD'
    TIME = "Time"
    SECTION = "Section"
    LEFT_THRESHOLD = "left_threshold"
    RIGHT_THRESHOLD = "right_threshold"
    OLD_TIME_DIFF_SEC = "old_TIME_DIFF_SEC"
    OLD_MODIFIED_Z_SCORE = "old_modified_zscore"

REDUNDANT_COLUMNS = [ExcelColumnName.OLD_TIME_DIFF_SEC.value, 
                        ExcelColumnName.OLD_MODIFIED_Z_SCORE.value, 
                        ExcelColumnName.LEFT_THRESHOLD.value, 
                        ExcelColumnName.RIGHT_THRESHOLD.value]

class ExcelColumnIndex(enum.Enum):
    FORMATTED_TIME = 2
    TIME_DIFF_SEC = 4
    TIME_DIFF_SEC_HH_MM_SS = 5
    EVENT_CONTEXT = 9

class ThresholdType(enum.Enum):
    TEN_MINUTES = 0
    THIRTY_MINUTES = 5
    INTERQUARTILE_RANGE = 10
    MODIFIED_Z_SCORE = 15 

DEFAULT_DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FILE_DIR = r'F:\E\code\student-data-project\resources'
OUTPUT_FILE_DIR = FILE_DIR
FILE_NAME = 'CORRECTED ROSTER.xlsx'
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
    start_time = df.at[start_time_index, ExcelColumnName.FORMATTED_TIME.value] 
    end_time = df.at[end_time_index, ExcelColumnName.FORMATTED_TIME.value]
    start_time = datetime.datetime.strptime(start_time, DEFAULT_DATE_TIME_FORMAT)
    end_time = datetime.datetime.strptime(end_time, DEFAULT_DATE_TIME_FORMAT)
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

def delete_invalid_users(input_file_path, output_file_path):

    df = pd.read_csv(input_file_path)
    df[ExcelColumnName.EVENT_CONTEXT.value] = df[ExcelColumnName.EVENT_CONTEXT.value].str.lower() #change all event name to lower case
    write_df_to_csv(file_path = os.path.join(OUTPUT_FILE_DIR, output_file_path), df = df)

#change all event name to lower case
#for each event, compute it's duration (end_time-start_time)
#add a new column to represent Event_duration in HH:MM:SS
def compute_event_duration(input_file_path, output_file_path):

    df = pd.read_csv(input_file_path)
    
    #df[ExcelColumnName.DATE_TIME.value] = df[ExcelColumnName.DATE_TIME.value].astype('str')
    
    df.reset_index(drop = True, inplace = True)

    df.insert(ExcelColumnIndex.TIME_DIFF_SEC.value, ExcelColumnName.TIME_DIFF_SEC.value, "") #add a new column to represent event duration in hh:mm:ss
    df.insert(ExcelColumnIndex.TIME_DIFF_SEC_HH_MM_SS.value, ExcelColumnName.TIME_DIFF_HH_MM_SS.value, "") #add a new column to represent event duration in hh:mm:ss

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

#private function used by "fix_long_events_duration" to fix.
# for non quiz events(event name doesn't start with "quiz: exam" or "quiz: final exam"), 
#   return threshold if it's duration is greater than the threshold
# for all other events return their duration
def fix_outlier_by_single_threshold(row, stat_df, threshold):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    if time_diff_sec > threshold:
        event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
        if not (event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam')):
            return threshold
    return time_diff_sec

#private function used by "fix_long_events_duration" to fix
#only updates the duration of the last events by threshold
def fix_last_event_outlier_by_single_threshold(row, stat_df, threshold):

    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    is_last_event = row[ExcelColumnName.IS_LAST_EVENT.value]
    if is_last_event and (time_diff_sec > threshold):
        event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
        if not (event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam')):
            return threshold
    return time_diff_sec

# #private function used by "fix_long_events_duration" to fix
# #only updates the duration of the last events by threshold
# def fix_last_event_outlier_by_single_threshold(row, stat_df, threshold):

#     time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
#     is_last_event = row[ExcelColumnName.IS_LAST_EVENT.value]
#     if is_last_event and (time_diff_sec > threshold):
#         event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
#         if not (event_context.startswith('quiz: exam') or event_context.startswith('quiz: final exam')):
#             return threshold
#         else:
#             return stat_df.at[event_context, "50%"]
#     return time_diff_sec

def update_duration(value, default_value, left_threshold, right_threshold, left_outlier_replacement_val, right_outlier_replacement_val):
    
    if value < left_threshold:
        return left_outlier_replacement_val
    if value > right_threshold:
        return right_outlier_replacement_val
    return default_value

def is_exam(event_context):
    return event_context.startswith("quiz: exam") or event_context.startswith("quiz: final exam")

def get_iqr_threshold_value(row, stat_df):
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    interquartile_range = stat_df.at[event_context, "75%"] - stat_df.at[event_context, "25%"] 
    left_threshold = stat_df.at[event_context, "25%"] - 1.5 * interquartile_range 
    right_threshold = stat_df.at[event_context, "75%"] + 1.5 * interquartile_range
    return pd.Series((left_threshold, right_threshold))

def get_modified_zscore_threshold_value(row, stat_df):
    
    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]

    medianAD = stat_df.at[event_context, ExcelColumnName.MEDIAN_AD.value]
    meanAD = stat_df.at[event_context, ExcelColumnName.MEAN_AD.value]

    #talk:
    #redundant check: if meanAD is 0, medianAD should be also 0
    if medianAD == 0 and meanAD == 0:
        return pd.Series((None, None, None))

    median = stat_df.at[event_context, '50%']
    left_threshold_z_score = -3.5
    right_threshold_z_score = 3.5
    
    #https://www.ibm.com/docs/en/cognos-analytics/11.1.0?topic=terms-modified-z-score
    if medianAD == 0:
        CONSTANT_FACTOR = 1.253314
        modified_z_score = (time_diff_sec-median) / (CONSTANT_FACTOR * meanAD)
        left_threshold = left_threshold_z_score * CONSTANT_FACTOR * meanAD + median
        right_threshold = right_threshold_z_score * CONSTANT_FACTOR * meanAD + median
    else:
        CONSTANT_FACTOR = 1.486
        modified_z_score = (time_diff_sec-median)/(CONSTANT_FACTOR * medianAD)
        left_threshold = left_threshold_z_score * CONSTANT_FACTOR * medianAD + median
        right_threshold = right_threshold_z_score * CONSTANT_FACTOR * medianAD + median
    return pd.Series((modified_z_score, left_threshold, right_threshold))


def update_duration_by_interquartile_range(row, stat_df):

    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    if is_exam(event_context):
        return row[ExcelColumnName.TIME_DIFF_SEC.value]

    interquartile_range = stat_df.at[event_context, "75%"] - stat_df.at[event_context, "25%"] 
    left_threshold = stat_df.at[event_context, "25%"] - 1.5 * interquartile_range 
    right_threshold = stat_df.at[event_context, "75%"] + 1.5 * interquartile_range
    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    return update_duration(
                value = time_diff_sec, 
                default_value = time_diff_sec, 
                left_threshold = left_threshold, 
                right_threshold = right_threshold, 
                left_outlier_replacement_val = left_threshold,
                right_outlier_replacement_val= right_threshold)

def update_last_events_duration_by_interquartile_range(row, stat_df):

    if row[ExcelColumnName.IS_LAST_EVENT.value]:
        return update_duration_by_interquartile_range(row, stat_df)
    else:
        return row[ExcelColumnName.TIME_DIFF_SEC.value]
        
        
def update_duration_by_modified_z_score(row, stat_df):
    
    time_diff_sec = row[ExcelColumnName.TIME_DIFF_SEC.value]
    event_context = row[ExcelColumnName.EVENT_CONTEXT.value]
    
    if is_exam(event_context):
        return time_diff_sec

    medianAD = stat_df.at[event_context, ExcelColumnName.MEDIAN_AD.value]
    meanAD = stat_df.at[event_context, ExcelColumnName.MEAN_AD.value]

    #talk:
    #redundant check: if meanAD is 0, medianAD should be also 0
    if medianAD == 0 and meanAD == 0:
        return time_diff_sec

    median = stat_df.at[event_context, '50%']
    left_threshold = -3.5
    right_threshold = 3.5
    
    #https://www.ibm.com/docs/en/cognos-analytics/11.1.0?topic=terms-modified-z-score
    if medianAD == 0:
        CONSTANT_FACTOR = 1.253314
        modified_z_score = (time_diff_sec-median) / (CONSTANT_FACTOR * meanAD)
        left_outlier_replacement_value = left_threshold * CONSTANT_FACTOR * meanAD + median
        right_outlier_replacement_value = right_threshold * CONSTANT_FACTOR * meanAD + median
    else:
        CONSTANT_FACTOR = 1.486
        modified_z_score = (time_diff_sec-median)/(CONSTANT_FACTOR * medianAD)
        left_outlier_replacement_value = left_threshold * CONSTANT_FACTOR * medianAD + median
        right_outlier_replacement_value = right_threshold * CONSTANT_FACTOR * medianAD + median
    

    return update_duration(
                value = modified_z_score, 
                default_value = time_diff_sec, 
                left_threshold = left_threshold, 
                right_threshold = right_threshold, 
                left_outlier_replacement_val = left_outlier_replacement_value,
                right_outlier_replacement_val= right_outlier_replacement_value)


def update_last_events_duration_by_modified_z_score(row, stat_df):
    
    if row[ExcelColumnName.IS_LAST_EVENT.value]:
        return update_duration_by_modified_z_score(row, stat_df)
    else:
        return row[ExcelColumnName.TIME_DIFF_SEC.value]

# add new new column in the name "is_last_event"
# is_last_event = true, when an event is a single event or it's the last event in a series of same event
def mark_last_events(input_file_path, output_file_path):
    
    print("Task: mark last events started..")
    df = pd.read_csv(input_file_path)
    df[ExcelColumnName.IS_LAST_EVENT.value] = False
    last_event = None
    last_student = None

    for index in df.index:

        event = df.at[index, ExcelColumnName.EVENT_CONTEXT.value]
        student = df.at[index, ExcelColumnName.USER_FULL_NAME.value]
        if student != last_student or event != last_event:
            df.at[index, ExcelColumnName.IS_LAST_EVENT.value] = True
        last_event = event
        last_student = student

    write_df_to_csv(output_file_path, df)
    print("Task: mark last events finished..")

#computes Median Absolute Deviation(MAD) for given series, s
def compute_MedianAD(s):
    median_s = s.median()
    return (abs(s-median_s)).median()

#computes Mean Absolute Deviation(MAD) for given series, s
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
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_last_event_outlier_by_single_threshold(row, stat_df, threshold=TEN_MINUTES_IN_SEC), axis = 1)
    elif by == ThresholdType.THIRTY_MINUTES:
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_outlier_by_single_threshold(row, stat_df, threshold=THIRTY_MINUTES_IN_SEC), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : fix_last_event_outlier_by_single_threshold(row, stat_df, threshold=THIRTY_MINUTES_IN_SEC), axis = 1)

    elif by == ThresholdType.INTERQUARTILE_RANGE:
        #the threshold column will be inserted before time_diff_sec column
        time_diff_sec_index = list(df.columns).index(ExcelColumnName.TIME_DIFF_SEC.value)
        df.insert(time_diff_sec_index, ExcelColumnName.RIGHT_THRESHOLD.value, 0)
        df.insert(time_diff_sec_index, ExcelColumnName.LEFT_THRESHOLD.value, 0)
        df.insert(time_diff_sec_index, ExcelColumnName.OLD_TIME_DIFF_SEC.value, 0)
        
        
        df[ExcelColumnName.OLD_TIME_DIFF_SEC.value] = df[ExcelColumnName.TIME_DIFF_SEC.value]
        df[[ExcelColumnName.LEFT_THRESHOLD.value, ExcelColumnName.RIGHT_THRESHOLD.value]] = df.apply(lambda row : 
                get_iqr_threshold_value(row, stat_df), axis = 1)
        
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_duration_by_interquartile_range(row, stat_df), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_last_events_duration_by_interquartile_range(row, stat_df), axis = 1)
   
    elif by == ThresholdType.MODIFIED_Z_SCORE:
       #compute MAD for each event_context
        stat_df[ExcelColumnName.MEDIAN_AD.value] = stat_df.apply(lambda row : compute_MedianAD(df[df[ExcelColumnName.EVENT_CONTEXT.value] == row.name][ExcelColumnName.TIME_DIFF_SEC.value]), axis = 1)
        stat_df[ExcelColumnName.MEAN_AD.value] = stat_df.apply(lambda row : compute_MeanAD(df[df[ExcelColumnName.EVENT_CONTEXT.value] == row.name][ExcelColumnName.TIME_DIFF_SEC.value]), axis = 1)
        write_df_to_csv(os.path.join(OUTPUT_FILE_DIR, 'updated_stat_df.csv'), stat_df)
        
        #the threshold column will be inserted before time_diff_sec column
        time_diff_sec_index = list(df.columns).index(ExcelColumnName.TIME_DIFF_SEC.value)
        df.insert(time_diff_sec_index, ExcelColumnName.RIGHT_THRESHOLD.value, 0)
        df.insert(time_diff_sec_index, ExcelColumnName.LEFT_THRESHOLD.value, 0)
        df.insert(time_diff_sec_index, ExcelColumnName.OLD_MODIFIED_Z_SCORE.value, 0)
        df.insert(time_diff_sec_index, ExcelColumnName.OLD_TIME_DIFF_SEC.value, 0)
        
        df[ExcelColumnName.OLD_TIME_DIFF_SEC.value] = df[ExcelColumnName.TIME_DIFF_SEC.value]

        df[[ExcelColumnName.OLD_MODIFIED_Z_SCORE.value, ExcelColumnName.LEFT_THRESHOLD.value, ExcelColumnName.RIGHT_THRESHOLD.value]] = df.apply(lambda row : 
                get_modified_zscore_threshold_value(row, stat_df), axis = 1)
        if all_events:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_duration_by_modified_z_score(row, stat_df), axis = 1)
        else:
            df[ExcelColumnName.TIME_DIFF_SEC.value] = df.apply(lambda row : update_last_events_duration_by_modified_z_score(row, stat_df), axis = 1)

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
    columns_to_del = [ column for column in REDUNDANT_COLUMNS if column in df]
    df.drop(columns=columns_to_del, inplace=True)

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
                    active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value] = SINGLE_EVENTS_PREFIX + active_row_as_list[ExcelColumnIndex.EVENT_CONTEXT.value]
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

TIME_PATTERN = [
    r"^\d+:\d+\s[AP]M,[A-Z][a-z]{2}\s\d+$",
    r"^\d+/\d+/\d+\s\d+:\d+:\d+$",
    r"^\d+:\d+/\d+$"
]

DATE_TIME_FORMAT = [
    r"%Y:%I:%M %p,%b %d",
    r"%m/%d/%y %H:%M:%S",
    r"%H:%M%m/%d/%Y"
]

#convert given tm string to datetime
def fix(section, tm):
    try:
        year, semester = section.split()
        year = int(year)
        if re.match(TIME_PATTERN[0], tm):
            tm = "2016:" + tm
            date_time = datetime.datetime.strptime(tm, DATE_TIME_FORMAT[0])
        elif re.match(TIME_PATTERN[1], tm):
            date_time = datetime.datetime.strptime(tm, DATE_TIME_FORMAT[1])
        elif re.match(TIME_PATTERN[2], tm):
            tm = tm + "/2016"
            date_time = datetime.datetime.strptime(tm, DATE_TIME_FORMAT[2])
        else:
            raise Exception("Invalid date time " + tm)
        
        if semester == "FF" and date_time.month < 7:
            year = year + 1

        date_time = date_time.replace(year = year)
    except Exception as e:
        print(e)
        print(tm)
        print(section)
        raise Exception("Date error")
    return date_time
        

    
    
#convert all time to a uniform format. add a new column for that format.
def fix_time_format(input_file, output_file):
    df = pd.read_excel(input_file)
    tm = df.apply(lambda row : fix(row[ExcelColumnName.SECTION.value], row[ExcelColumnName.TIME.value]), axis = 1)
    df.insert(ExcelColumnIndex.FORMATTED_TIME.value, ExcelColumnName.FORMATTED_TIME.value, tm)
    write_df_to_csv(output_file, df)


if __name__ == "__main__":

    formatted_time_output_file_name = "formatted_time.csv"
    deleted_invalid_users_output_file_name = "0_invalid_users_deleted.csv"
    event_duration_output_file_name = '1_event_duration.csv'
    students_last_event_deleted_file_name = '2_students_last_event_deleted.csv'
    negative_time_fixed_file_name = "3_negative_time_fixed.csv"
    reset_last_quiz_events_duration_file_name = "4_reset_last_quiz_events_duration.csv"
    zero_duration_event_deleted_file_name = "5_zero_duration_event_deleted.csv"
    statistics_output_file_name = '6_statistics.csv'
    marked_last_events_file_name = "7_marked_last_events.csv"
    
    outlier_fixed_by_10_min_all_event_output_file_name = '7a_outlier_fixed_by_10min_threshold_all_event.csv'
    outlier_fixed_by_10_min_last_only_output_file_name = '7b_outlier_fixed_by_10min_threshold_last_only.csv'
    outlier_fixed_by_30_min_all_event_output_file_name = '7c_outlier_fixed_by_30min_threshold_all_event.csv'
    outlier_fixed_by_30_min_last_only_output_file_name = '7d_outlier_fixed_by_30min_threshold_last_only.csv'
    outlier_fixed_by_iqr_all_event_output_file_name = '7e_outlier_fixed_by_iqr_all_event.csv'
    outlier_fixed_by_iqr_last_only_output_file_name = '7f_outlier_fixed_by_iqr_last_only.csv'
    outlier_fixed_by_modz_all_event_output_file_name = '7g_outlier_fixed_by_mod_z_score_all_event.csv'
    outlier_fixed_by_modz_last_only_output_file_name = '7h_outlier_fixed_by_mod_z_score_last_only.csv'

    outlier_fixed_file_name_list = [    
        outlier_fixed_by_10_min_all_event_output_file_name,
        outlier_fixed_by_10_min_last_only_output_file_name,
        outlier_fixed_by_30_min_all_event_output_file_name,
        outlier_fixed_by_30_min_last_only_output_file_name,
        outlier_fixed_by_iqr_all_event_output_file_name,
        outlier_fixed_by_iqr_last_only_output_file_name,
        outlier_fixed_by_modz_all_event_output_file_name,
        outlier_fixed_by_modz_last_only_output_file_name
    ]
    
    aggregated_events_10_min_all_output_file_name = "8a_aggregated_events_10_min_all.csv"
    aggregated_events_10_min_last_only_output_file_name = "8b_aggregated_events_10_min_last_only.csv"
    aggregated_events_30_min_all_output_file_name = "8c_aggregated_events_30_min_all.csv"
    aggregated_events_30_min_last_only_output_file_name = "8d_aggregated_events_30_min_last_only.csv"
    aggregated_events_iqr_all_output_file_name = "8e_aggregated_events_iqr_all.csv"
    aggregated_events_iqr_last_only_output_file_name = "8f_aggregated_events_iqr_last_only.csv"
    aggregated_events_modz_all_output_file_name = "8g_aggregated_events_modz_all.csv"
    aggregated_events_modz_last_only_output_file_name = "8h_aggregated_events_modz_last_only.csv"

    aggregated_events_file_name_list = [
        aggregated_events_10_min_all_output_file_name,
        aggregated_events_10_min_last_only_output_file_name,
        aggregated_events_30_min_all_output_file_name,
        aggregated_events_30_min_last_only_output_file_name,
        aggregated_events_iqr_all_output_file_name,
        aggregated_events_iqr_last_only_output_file_name,
        aggregated_events_modz_all_output_file_name,
        aggregated_events_modz_last_only_output_file_name
    ]
    
    single_quiz_events_deleted_10_min_all_output_file_name = "9a_single_quiz_events_deleted_10_min_all.csv"
    single_quiz_events_deleted_10_min_last_only_output_file_name = "9b_single_quiz_events_deleted_10_min_last_only.csv"
    single_quiz_events_deleted_30_min_all_output_file_name = "9c_single_quiz_events_deleted_30_min_all.csv"
    single_quiz_events_deleted_30_min_last_only_output_file_name = "9d_single_quiz_events_deleted_30_min_last_only.csv"
    single_quiz_events_deleted_iqr_all_output_file_name = "9e_single_quiz_events_deleted_iqr_all.csv"
    single_quiz_events_deleted_iqr_last_only_output_file_name = "9f_single_quiz_events_deleted_iqr_last_only.csv"
    single_quiz_events_deleted_modz_all_output_file_name = "9g_single_quiz_events_deleted_modz_all.csv"
    single_quiz_events_deleted_modz_last_only_output_file_name = "9h_single_quiz_events_deleted_modz_last_only.csv"

    single_quiz_events_deleted_file_name_list = [
        single_quiz_events_deleted_10_min_all_output_file_name,
        single_quiz_events_deleted_10_min_last_only_output_file_name,
        single_quiz_events_deleted_30_min_all_output_file_name,
        single_quiz_events_deleted_30_min_last_only_output_file_name,
        single_quiz_events_deleted_iqr_all_output_file_name,
        single_quiz_events_deleted_iqr_last_only_output_file_name,
        single_quiz_events_deleted_modz_all_output_file_name,
        single_quiz_events_deleted_modz_last_only_output_file_name
    ]

    duplicate_quiz_events_deleted_10_min_all_output_file_name = "10a_duplicate_quiz_events_deleted_10_min_all.csv"
    duplicate_quiz_events_deleted_10_min_last_only_output_file_name = "10b_duplicate_quiz_events_deleted_10_min_last_only.csv"
    duplicate_quiz_events_deleted_30_min_all_output_file_name = "10c_duplicate_quiz_events_deleted_30_min_all.csv"
    duplicate_quiz_events_deleted_30_min_last_only_output_file_name = "10d_duplicate_quiz_events_deleted_30_min_last_only.csv"
    duplicate_quiz_events_deleted_iqr_all_output_file_name = "10e_duplicate_quiz_events_deleted_iqr_all.csv"
    duplicate_quiz_events_deleted_iqr_last_only_output_file_name = "10f_duplicate_quiz_events_deleted_iqr_last_only.csv"
    duplicate_quiz_events_deleted_modz_all_output_file_name = "10g_duplicate_quiz_events_deleted_modz_all.csv"
    duplicate_quiz_events_deleted_modz_last_only_output_file_name = "10h_duplicate_quiz_events_deleted_modz_last_only.csv"
    
    duplicate_quiz_events_deleted_file_name_list = [
        duplicate_quiz_events_deleted_10_min_all_output_file_name,
        duplicate_quiz_events_deleted_10_min_last_only_output_file_name,
        duplicate_quiz_events_deleted_30_min_all_output_file_name,
        duplicate_quiz_events_deleted_30_min_last_only_output_file_name,
        duplicate_quiz_events_deleted_iqr_all_output_file_name,
        duplicate_quiz_events_deleted_iqr_last_only_output_file_name,
        duplicate_quiz_events_deleted_modz_all_output_file_name,
        duplicate_quiz_events_deleted_modz_last_only_output_file_name
    ]


    aggregated_events_statistics_10_min_all_output_file_name = "11a_aggregated_events_statistics_10_min_all.csv"
    aggregated_events_statistics_10_min_last_only_output_file_name = "11b_aggregated_events_statistics_10_min_last_only.csv"
    aggregated_events_statistics_30_min_all_output_file_name = "11c_aggregated_events_statistics_30_min_all.csv"
    aggregated_events_statistics_30_min_last_only_output_file_name = "11d_aggregated_events_statistics_30_min_last_only.csv"
    aggregated_events_statistics_iqr_all_output_file_name = "11e_aggregated_events_statistics_iqr_all.csv"
    aggregated_events_statistics_iqr_last_only_output_file_name = "11f_aggregated_events_statistics_iqr_last_only.csv"
    aggregated_events_statistics_modz_all_output_file_name = "11g_aggregated_events_statistics_modz_all.csv"
    aggregated_events_statistics_modz_last_only_output_file_name = "11h_aggregated_events_statistics_modz_last_only.csv"


    aggregated_events_statistics_file_name_list = [
        aggregated_events_statistics_10_min_all_output_file_name,
        aggregated_events_statistics_10_min_last_only_output_file_name,
        aggregated_events_statistics_30_min_all_output_file_name,
        aggregated_events_statistics_30_min_last_only_output_file_name,
        aggregated_events_statistics_iqr_all_output_file_name,
        aggregated_events_statistics_iqr_last_only_output_file_name,
        aggregated_events_statistics_modz_all_output_file_name,
        aggregated_events_statistics_modz_last_only_output_file_name
    ]
    
    # fix_time_format(FILE_PATH, 
    #                     os.path.join(OUTPUT_FILE_DIR, formatted_time_output_file_name))
    #check_single_events(os.path.join(OUTPUT_FILE_DIR, '4_zero_duration_event_deleted.csv'))
    # delete_invalid_users(os.path.join(OUTPUT_FILE_DIR, formatted_time_output_file_name),
    #                     output_file_path = os.path.join(OUTPUT_FILE_DIR, deleted_invalid_users_output_file_name))
    # compute_event_duration(os.path.join(OUTPUT_FILE_DIR, deleted_invalid_users_output_file_name),
    #                     output_file_path = os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name))
    # delete_students_last_event(os.path.join(OUTPUT_FILE_DIR, event_duration_output_file_name), 
    #                     output_file_path = os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name))
    # fix_negative_time(os.path.join(OUTPUT_FILE_DIR, students_last_event_deleted_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name))
    # reset_last_quiz_events_duration(os.path.join(OUTPUT_FILE_DIR, negative_time_fixed_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, reset_last_quiz_events_duration_file_name))
    # delete_zero_duration_event(os.path.join(OUTPUT_FILE_DIR, reset_last_quiz_events_duration_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name))
    # generate_statistics(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name),
    #                     os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name))
    # mark_last_events(os.path.join(OUTPUT_FILE_DIR, zero_duration_event_deleted_file_name), 
    #                     os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name))

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_10_min_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.TEN_MINUTES, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_10_min_last_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.TEN_MINUTES, 
    #                         all_events = False)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_30_min_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.THIRTY_MINUTES, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_30_min_last_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.THIRTY_MINUTES, 
    #                         all_events = False)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_iqr_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.INTERQUARTILE_RANGE, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_iqr_last_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.INTERQUARTILE_RANGE, 
    #                         all_events = False)


    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_modz_all_event_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.MODIFIED_Z_SCORE, 
    #                         all_events = True)

    # fix_outliers(os.path.join(OUTPUT_FILE_DIR, marked_last_events_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, outlier_fixed_by_modz_last_only_output_file_name), 
    #                         os.path.join(OUTPUT_FILE_DIR, statistics_output_file_name), 
    #                         ThresholdType.MODIFIED_Z_SCORE, 
    #                         all_events = False)

    for (outlier_fixed_file_name, aggregated_events_file_name) in zip(outlier_fixed_file_name_list, aggregated_events_file_name_list):
        aggregate_events(os.path.join(OUTPUT_FILE_DIR, outlier_fixed_file_name),
                        os.path.join(OUTPUT_FILE_DIR, aggregated_events_file_name))

    import time
    #not needed
    # for (aggregated_events_file_name, single_quiz_events_deleted_file_name) in zip(aggregated_events_file_name_list, single_quiz_events_deleted_file_name_list):
    #     delete_single_quiz_events(os.path.join(OUTPUT_FILE_DIR, aggregated_events_file_name), 
    #                             os.path.join(OUTPUT_FILE_DIR, single_quiz_events_deleted_file_name))
    #     time.sleep(60)
    
    # for (aggregated_events_file_name, duplicate_quiz_events_deleted_file_name) in zip(aggregated_events_file_name_list, duplicate_quiz_events_deleted_file_name_list):
    #     delete_duplicate_quiz_events(os.path.join(OUTPUT_FILE_DIR, aggregated_events_file_name), 
    #                                 os.path.join(OUTPUT_FILE_DIR, duplicate_quiz_events_deleted_file_name))
    #     time.sleep(55)

    # for (duplicate_quiz_events_deleted_file_name, aggregated_events_statistics_file_name) in zip(duplicate_quiz_events_deleted_file_name_list, aggregated_events_statistics_file_name_list):
    #     generate_statistics(os.path.join(OUTPUT_FILE_DIR, duplicate_quiz_events_deleted_file_name), 
    #         os.path.join(OUTPUT_FILE_DIR, aggregated_events_statistics_file_name), remove_event_prefix = True)
        # time.sleep(60)

