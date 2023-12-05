import mat73
from datetime import datetime
import numpy as np
import pandas as pd
import os 
import tqdm 
# Combine date and time into a datetime object
def get_time_from_filename(filename):
    # filename in format blabla_y,m,d_h,m,s.mat
    # returns timestamp obect
    date_str = filename.replace('.mat','').split('_')[-2]
    time_str = filename.replace('.mat','').split('_')[-1]

    date_object = datetime.strptime(date_str, '%Y%m%d')
    time_object = datetime.strptime(time_str, '%H%M%S').time()

    # Combine date and time into a datetime object
    start = datetime.combine(date_object.date(), time_object)   
    return start

def select_time_snippet(data,startTime,eventTime,windowsize,Fs):
    # takes a piece of signal of shape [channel, ts], the timestamp of the event, the start of the eeg and the windowsize
    # returns the event pm windowsize, shape [channel, windowsize]

    SecondsAfterStart = int((eventTime-startTime).total_seconds())
    start = int((SecondsAfterStart-windowsize/2)*Fs)
    end = int((SecondsAfterStart+windowsize/2)*Fs)
    return data[:,start:end]

def select_channels(data,available_channels,desired_channels):
    desired_channel_ids = [available_channels.index(channel) for channel in desired_channels]
    eeg_data = data[desired_channel_ids,:]
    if 'ECGL' in available_channels:
        ecg_data = data[available_channels.index('ECGL'),:]-data[available_channels.index('ECGR')]
    elif 'EKG1' in available_channels:
        ecg_data = data[available_channels.index('EKG1'),:]-data[available_channels.index('EKG2')]
    elif 'EKG' in available_channels:
        ecg_data = data[available_channels.index('EKG'),:]
    else:
        print('no EKG DATA')
        print('available: data: '+available_channels)
    data = np.vstack([eeg_data,ecg_data])
    return data

# for a given eeg file, generate the path to the .mat file
def generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,eeg_start_time,index):
    # generate path to file and filename
    path = SiteID+'/'+EEGFolder+'/'+HashFolderName+'/'
    # insert 0 to create Hashfoldername_0_date_time
    # if next:
    #     eeg_start_time = eeg_start_time+timedelta(hours=12)
    #     index = 1
    eeg_start_time_str = datetime.strftime(eeg_start_time,'%Y%m%d_%H%M%S')
    filename = '_'.join([HashFolderName.split('_')[0],str(index),eeg_start_time_str])+'.mat'
    return os.path.join(root,path,filename)

def load_signal_and_data(path_file):
    # load signal and data
    signal = mat73.loadmat(path_file)
    data=signal['data']
    Fs=signal['Fs']
    channels=signal['channels']

    return data,Fs,channels

if __name__ == '__main__':
    print('loading dataframes')
    # load table with event data
    df_event = pd.read_excel('tables/batch1.xlsx')
    df_event = df_event.rename({'file':'HashFolderName','time':'eventTime'},axis=1)
    
    # load and extract starttime
    df_eeg = pd.read_csv('work_tables/EEGs_And_Reports_20231024.csv')[['HashFolderName','SiteID','SessionID_new','EEGFolder']]
    df_eeg['startTime'] = df_eeg.HashFolderName.apply(get_time_from_filename)
    df_eeg = df_eeg.drop_duplicates('HashFolderName')

    # set some parameters
    # root folder of eeg files 
    root = 'bdsp/opendata/EEG/data/'
    # windowsize of extracted window
    windowsize = 15
    # channels to extract
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']
                  
    print('starting file extraction')
    for HashFolderName in tqdm.tqdm(df_event.HashFolderName.unique()[3:]):

        # get info from eeg singnal and load data
        eeg_info = df_eeg[df_eeg.HashFolderName==HashFolderName].iloc[0]
        SiteID, EEGFolder,HashFolderName,startTime = eeg_info.SiteID,eeg_info.EEGFolder,eeg_info.HashFolderName,eeg_info.startTime
        eeg_path = generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,startTime,index=0)
        print('loading data')
        data,Fs,available_channels = load_signal_and_data(eeg_path)    
        for eventTime in df_event[df_event.HashFolderName == HashFolderName]['eventTime']:
            # there is a bug with some files, so that their times are wrong
            if (eventTime-startTime).total_seconds()>1000000:
                continue
            # some files are cut in half after 12h, so a seperate file needs to be loaded!
            if (eventTime-startTime).total_seconds()>data.shape[1]/Fs:
                startTime = startTime+timedelta(hours=12)
                eeg_path = generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,startTime,index=1)
                data,Fs,available_channels = load_signal_and_data(eeg_path)
            
            signal = select_time_snippet(data=data,startTime=startTime,eventTime=eventTime,windowsize=windowsize,Fs=Fs)
            signal = select_channels(data=signal,desired_channels=desired_channels,available_channels=channels)
            name = HashFolderName.split('_')[0]+'_'+datetime.strftime(eventTime,'%Y%m%d_%H%M%S')
            
