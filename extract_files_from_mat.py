import mat73
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import os 
import tqdm 
import tempfile
import shutil
import argparse
from utils import *
import h5py

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

def save_events_npy(data,HashFolderName,startTime,eventTimes,windowsize,desired_channels,available_channels,path_save):
    # save all events in eventTimes as numpy arrays, using snippets of length windowsize and channels desired_channels
    # naming convention is HashFolderName_eventTime.npy
    for eventTime in tqdm.tqdm(eventTimes,leave=False):
            # select time snippet and correct channels
            signal = select_time_snippet(data=data,startTime=startTime,eventTime=eventTime,windowsize=windowsize,Fs=Fs)
            signal = select_channels(data=signal,desired_channels=desired_channels,available_channels=available_channels)
            # generate filename
            name = HashFolderName.split('_')[0]+'_'+datetime.strftime(eventTime,'%Y%m%d_%H%M%S')
            # skip signals that are all nan
            if not np.isnan(signal).all():
                np.save(os.path.join(path_save,name+'.npy'),signal)

def save_events_h5(data,HashFolderName,startTime,eventTimes,windowsize,desired_channels,available_channels,hf):
    # save all events in eventTimes as numpy arrays, using snippets of length windowsize and channels desired_channels
    # naming convention is HashFolderName_eventTime.npy
    for eventTime in tqdm.tqdm(eventTimes,leave=False):
            # select time snippet and correct channels
            signal = select_time_snippet(data=data,startTime=startTime,eventTime=eventTime,windowsize=windowsize,Fs=Fs)
            signal = select_channels(data=signal,desired_channels=desired_channels,available_channels=available_channels)
            # generate filename
            name = HashFolderName.split('_')[0]+'_'+datetime.strftime(eventTime,'%Y%m%d_%H%M%S')
            # skip signals that are all nan
            if not np.isnan(signal).all():
                hf.create_dataset(name, data=signal,dtype='f4',compression='gzip')
            

def write_to_error(message,echo=True):
    # if an error occurs, write it to errors.txt
    with open('errors.txt', 'a') as f:
        f.write(message+'\n')
        f.close()
    if echo:
        print(message)

def load_df_eeg():
    df_eeg = pd.read_csv('tables/EEGs_And_Reports_20231024.csv')[['HashFolderName','SiteID','SessionID_new','EEGFolder']]
    df_eeg['startTime'] = df_eeg.HashFolderName.apply(get_time_from_filename)
    df_eeg = df_eeg.drop_duplicates('HashFolderName')
    return df_eeg

if __name__ == '__main__':
    # add argparser
    parser = argparse.ArgumentParser(description='Extract EEG files from mat files')
    parser.add_argument('--batch', type=str,default='tables/batch2_not_in_files', help='batch to process')
    parser.add_argument('--path_save', type=str, default='missing',help='path to save extracted files')

    batch = parser.parse_args().batch
    path_save = parser.parse_args().path_save

    hf = h5py.File(os.path.join(path_save,batch+'.h5'), 'w')


    print('loading dataframes')
    # load table with event data
    df_event = pd.read_excel('tables/'+batch+'.xlsx')
    df_event = df_event.rename({'file':'HashFolderName','time':'eventTime'},axis=1)
    # load and extract starttime
    df_eeg = load_df_eeg()
    # root folder of eeg files 
    root = 'bdsp/opendata/EEG/data/'
    # windowsize of extracted window
    windowsize = 15
    # channels to extract
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']
            
    print('starting file extraction')
    for HashFolderName in tqdm.tqdm(df_event.HashFolderName.unique()):
        # extract siteID, EEGFolder and startTime for HashFolder from df_eeg    
        SiteID,EEGFolder,startTime = df_eeg[df_eeg.HashFolderName == HashFolderName].iloc[0][['SiteID','EEGFolder','startTime']]
        # extract all eventTimes for HashFolder from df_event
        eventTimes = df_event[df_event.HashFolderName == HashFolderName]['eventTime'].unique()   

        pathFolder = os.path.join(root,SiteID,EEGFolder,HashFolderName)
        if not os.path.isdir(pathFolder):
            write_to_error(message='Folder does not exist '+pathFolder)
            continue
        
        if max(eventTimes)-startTime>timedelta(hours=1000):
            write_to_error(message='wrong startTime of file: '+HashFolderName)
            continue

        # eegs are split in 12h segments and stored with Hashfoldername_eegIndex_startTime
        eegIndex=0
        # get all eventtimes in first 12h segment
        saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 

        # for as long as there are eventtimes left, loop over 12h segments, save all events in that segment and remove them from eventTimes
        while len(eventTimes)>0:
            # only load 
            if len(saveTimes)>0:
                eeg_path = generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,startTime,index=eegIndex)
                eegIndex+=1
                if not os.path.isfile(eeg_path):
                    write_to_error(message='file does not exist '+eeg_path)
                    break
                data,Fs,available_channels = load_signal_and_data(eeg_path)
                # save all events in saveTimes
                #save_events(data,HashFolderName,startTime,saveTimes,windowsize,desired_channels,available_channels,path_save=path_save)
                save_events_h5(data,HashFolderName,startTime,saveTimes,windowsize,desired_channels,available_channels,hf=hf)
            # remove all eventtimes from this segment from eventTimes
            eventTimes = eventTimes[eventTimes>=startTime+timedelta(hours=12)] 
            # update startTime and saveTimes for next 12h segment
            startTime = startTime+timedelta(hours=12)
            saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+timedelta(hours=12))] 
    
        if os.path.isdir('/tmp/s3_cache/'):
            try: shutil.rmtree('/tmp/s3_cache/')
            except: print('failed to remove tmp, skipping')