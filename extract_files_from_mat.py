import mat73
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os 
import tqdm 
import tempfile
import shutil
from utils import *

# for a given eeg file, generate the path to the .mat file
def generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,eeg_start_time,index):
    # generate path to file and filename
    path = SiteID+'/'+EEGFolder+'/'+HashFolderName+'/'
    # insert 0 to create Hashfoldername_0_date_time
    eeg_start_time_str = datetime.strftime(eeg_start_time,'%Y%m%d_%H%M%S')
    filename = '_'.join([HashFolderName.split('_')[0],str(index),eeg_start_time_str])+'.mat'
    return os.path.join(root,path,filename)

def load_signal_and_data(path_file):
    # load signal and data
    mat = mat73.loadmat(path_file)
    data=mat['data']
    Fs=mat['Fs']
    channels=mat['channels']
    return data,Fs,channels

def save_events(data,HashFolderName,startTime,eventTimes,windowsize,desired_channels,available_channels,path_save):
    for eventTime in tqdm.tqdm(eventTimes,leave=False):
            signal = select_time_snippet(data=data,startTime=startTime,eventTime=eventTime,windowsize=windowsize,Fs=Fs)
            signal = select_channels(data=signal,desired_channels=desired_channels,available_channels=available_channels)
            name = HashFolderName.split('_')[0]+'_'+datetime.strftime(eventTime,'%Y%m%d_%H%M%S')
            
            np.save(os.path.join(path_save,name+'.npy'),signal)

def write_to_error(message,eeg_path):
    with open('errors.txt', 'w') as f:
        print(message+' '+eeg_path)
        f.write(message+' '+eeg_path)
        f.close()


if __name__ == '__main__':
    print('loading dataframes')
    # load table with event data
    df_event = pd.read_excel('tables/batch2.xlsx')
    df_event = df_event.rename({'file':'HashFolderName','time':'eventTime'},axis=1)
    # load and extract starttime
    df_eeg = pd.read_csv('tables/EEGs_And_Reports_20231024.csv')[['HashFolderName','SiteID','SessionID_new','EEGFolder']]
    df_eeg['startTime'] = df_eeg.HashFolderName.apply(get_time_from_filename)
    df_eeg = df_eeg.drop_duplicates('HashFolderName')

    # root folder of eeg files 
    root = 'bdsp/opendata/EEG/data/'
    # windowsize of extracted window
    windowsize = 15
    # channels to extract
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']
            
    print('starting file extraction')
    for HashFolderName in tqdm.tqdm(df_event.HashFolderName.unique()):
        HashFolder = df_event.HashFolderName.unique()[1]
        SiteID,EEGFolder = df_eeg[df_eeg.HashFolderName == HashFolderName].iloc[0][['SiteID','EEGFolder']]
        
        startTime = df_eeg[df_eeg.HashFolderName == HashFolderName].iloc[0]['startTime']
        eventTimes = df_event[df_event.HashFolderName == HashFolderName]['eventTime'].unique()
        saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 
            
        if eventTimes.max()-startTime>timedelta(hours=1000):
            write_to_error(message='wrong startTime of file',eeg_path=eeg_path)
            continue

        k=0
        while len(saveTimes)>0:
            # save all eventtimes in between 
            eeg_path = generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,startTime,index=k)
            k+=1
            if os.path.isfile(eeg_path):
                data,Fs,available_channels = load_signal_and_data(eeg_path)
                save_events(data,HashFolderName,startTime,saveTimes,windowsize,desired_channels,available_channels,path_save='files_batch_2/')
                startTime = startTime+timedelta(hours=12)
                saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 
            else:
                write_to_error(message='file does not exist',eeg_path=eeg_path)
                break
    
        if os.path.isdir('/tmp/s3_cache/'):
            try: shutil.rmtree('/tmp/s3_cache/')
            except: print('failed to remove tmp, skipping')