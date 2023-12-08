import mat73
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os 
import tqdm 
import h5py

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
        ecg_data = np.empty(1,data.shape[1])
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

def save_events(data,HashFolderName,startTime,eventTimes,windowsize,desired_channels,available_channels,path_save):
    for eventTime in tqdm.tqdm(eventTimes,leave=False):
            signal = select_time_snippet(data=data,startTime=startTime,eventTime=eventTime,windowsize=windowsize,Fs=Fs)
            signal = select_channels(data=signal,desired_channels=desired_channels,available_channels=available_channels)
            name = HashFolderName.split('_')[0]+'_'+datetime.strftime(eventTime,'%Y%m%d_%H%M%S')
            # hf.create_dataset(name=name,data=signal,dtype='f4',compression='gzip')
            np.save(os.path.join(path_save,name+'.npy'),signal)

if __name__ == '__main__':
    print('loading dataframes')
    # load table with event data
    df_event = pd.read_excel('tables/batch2.xlsx')
    df_event = df_event.rename({'file':'HashFolderName','time':'eventTime'},axis=1)
    
    # load and extract starttime
    # df_eeg = pd.read_csv('tables/EEGs_And_Reports_20231024.csv')[['HashFolderName','SiteID','SessionID_new','EEGFolder']]
    # df_eeg['startTime'] = df_eeg.HashFolderName.apply(get_time_from_filename)
    # df_eeg = df_eeg.drop_duplicates('HashFolderName')

    df_bids = pd.read_csv('tables/BIDS_EEG_MGB_Deidentified_Lookup_5thDecember.csv')
    df_bids['startTime']=df_bids.HashFolderName.apply(get_time_from_filename)
    # set some parametersf
    # root folder of eeg files 
    root = 'bdsp/opendata/EEG/bids'
    # windowsize of extracted window
    windowsize = 15
    # channels to extract
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']
    hf = h5py.File('SauronData.h5', 'w')
        
    
    print('starting file extraction')
    for HashFolderName in tqdm.tqdm(df_event.HashFolderName.unique()[:1]):
        HashFolder = df_event.HashFolderName.unique()[1]
        BidsFolder,ses_id = df_bids.loc[df_bids.HashFolderName==HashFolder,['BidsFolder',"SessionID"]].iloc[0]

        eventTimes = df_event[df_event.HashFolderName == HashFolderName]['eventTime'].unique()
        saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 
            
        if eventTimes.max()-startTime>timedelta(hours=1000):
            print('false file! '+eeg_path)
            continue

        k=0
        while len(saveTimes)>0:
            # save all eventtimes in between 
            eeg_path = generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,startTime,index=k)
            k+=1
            data,Fs,available_channels = load_signal_and_data(eeg_path)
            save_events(data,HashFolderName,startTime,saveTimes,windowsize,desired_channels,available_channels,path_save='test/')
            startTime = startTime+timedelta(hours=12)
            saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 
