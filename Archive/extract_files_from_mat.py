import pyedflib
import pandas as pd
#from extract_files_from_mat import * 
#import pyedflib
from datetime import timedelta, datetime
from tqdm import tqdm
import os
import numpy as np
import shutil
import argparse


def get_BidsFolder_info(df_bids,HashFolderName):
    BidsFolder,ses_id,startTime,EEGFolder = df_bids.loc[df_bids.HashFolderName==HashFolderName,['BidsFolder',"SessionID",'startTime','EEGFolder']].iloc[0]
    startTime = datetime.strptime(startTime, '%Y-%m-%d %H:%M:%S')
    return BidsFolder,ses_id,startTime,EEGFolder

def get_eventTimes(df,HashFolderName):
    eventTimes = df[df.HashFolderName == HashFolderName]['eventTime'].unique()
    return eventTimes

def get_saveTimes(eventTimes,startTime,data,Fs):
    # signal duration as timedelta
    signal_duration =  timedelta(seconds=data.shape[1]/Fs)
    saveTimes = eventTimes[(startTime<eventTimes)&(eventTimes<startTime+signal_duration)] 
    return saveTimes

def get_folderPath(root,BidsFolder,ses_id):
    folderPath = os.path.join(root,BidsFolder,'ses-'+str(ses_id),'eeg')
    return folderPath

def get_fileName(BidsFolder,ses_id,EEGFolder):
    fileName = '_'.join([BidsFolder,'ses-'+str(ses_id),'task-'+EEGFolder,'eeg.edf'])
    return fileName

def read_edf(folderPath,fileName,desired_channels):
    with pyedflib.EdfReader(os.path.join(folderPath,fileName)) as edf:
        labels = edf.getSignalLabels()
        desired_channel_ids = [labels.index(channel) for channel in desired_channels]
        
        eeg_data = [edf.readSignal(channel_id) for channel_id in desired_channel_ids]
        if 'ECGL' in labels:
            ecg_data = edf.readSignal(labels.index('ECGL'))-edf.readSignal(labels.index('ECGR'))           
        elif 'EKG1' in labels:
            ecg_data = edf.readSignal(labels.index('EKG1'))-edf.readSignal(labels.index('EKG2'))
        elif 'EKG' in labels:
            ecg_data = ecg_data = edf.readSignal(labels.index('EKG'))
        else:
            ecg_data = np.empty((1,data.shape[1]))
    
        signal = np.vstack([eeg_data,ecg_data])
        Fs = edf.getSampleFrequency(desired_channel_ids[0])
    return signal,Fs    

def load_file(folderPath,fileName,desired_channels):
    signal, Fs  = read_edf(folderPath,fileName,desired_channels)
    return signal,Fs

def save_event(path_save,name,signal,save_type='npy'):
    if save_type == 'npy':
        # Save as .npy file
        np.save(os.path.join(path_save, name + '.npy'), signal)
    elif save_type == 'h5':
        # Save in an HDF5 file
        with h5py.File(path_save, 'a') as hf:
            if name not in hf:
                hf.create_dataset(name, data=signal, dtype='f4', compression='gzip')
            else:
                write_to_error(path_error, message='Dataset already exists in the HDF5 file. {name}')

def write_to_error(path_error,message,echo=False):
    # if an error occurs, write it to errors.txt
    with open(path_error, 'a') as f:
        f.write(message+'\n')
        f.close()
    if echo:
        print(message)

def select_time_snippet(data,startTime,saveTime,windowsize,Fs):
    # takes a piece of signal of shape [channel, ts], the timestamp of the event, the start of the eeg and the windowsize
    # returns the event pm windowsize, shape [channel, windowsize]
    SecondsAfterStart = int((saveTime-startTime).total_seconds())
    start = int((SecondsAfterStart-windowsize/2)*Fs)
    end = int((SecondsAfterStart+windowsize/2)*Fs)
    return data[:,start:end]

def get_save_name(HashFolderName, eventTime):
    # Generate filename in the format HashFolderName_eventTime
    name = HashFolderName.split('_')[0] + '_' + datetime.strftime(eventTime, '%Y%m%d_%H%M%S')
    return name

def save_events(data,startTime,eventTimes,HashFolderName,windowsize,Fs,path_save,save_type='npy'):
    for saveTime in tqdm(eventTimes, leave=False):
        # Generate filename
        name = get_save_name(HashFolderName, saveTime)
        signal = select_time_snippet(data=data, startTime=startTime, saveTime=saveTime, windowsize=windowsize, Fs=Fs)
        if np.isnan(signal).all():
            write_to_error(path_error, message='event is allnan ' + name)
            continue
        save_event(path_save, name, signal, save_type=save_type)

def check_for_problems(path_error, pathFolder,fileName,startTime,eventTimes,HashFolderName):
    if max(eventTimes) - startTime > timedelta(hours=1000):
        write_to_error(path_error, message='startTime of file is wrong: ' + HashFolderName)
        return 'startTime wrong'
    if not os.path.isdir(pathFolder):
        write_to_error(path_error, message='Folder does not exist ' + pathFolder)
        return 'Folder not exist'

    if not os.path.isfile(os.path.join(pathFolder,fileName)):
        write_to_error(path_error, message='File does not exist ' + fileName)
        return 'File not exist'
    
    return 'OK'

def get_file_folder_and_name(df_bids,HashFolderName):
    BidsFolder,ses_id,startTime,EEGFolder = get_BidsFolder_info(df_bids,HashFolderName)
    folderPath = get_folderPath(root,BidsFolder,ses_id)
    fileName = get_fileName(BidsFolder,ses_id,EEGFolder)
    return folderPath,fileName, startTime

def clear_cache():
    if os.path.isdir('/tmp/s3_cache/'):
        try:
            shutil.rmtree('/tmp/s3_cache/')
        except Exception as e:
            print(f'Failed to remove tmp, skipping: {e}')
            
def get_info_from_parser():
    parser = argparse.ArgumentParser(description='Extract EEG files from mat files')
    parser.add_argument('--source_table', type=str,default='_to_do', help='xlsx file with HashFolderNames')
    parser.add_argument('--start_id', type=int,default=0, help='start id of HashFolder to process')
    parser.add_argument('--path_save', type=str,default='test', help='path to save data')
    parser.add_argument('--save_type', type=str,default='npy', help='file type to save data')
    source_table = parser.parse_args().source_table
    start_id = parser.parse_args().start_id
    path_save = parser.parse_args().path_save
    save_type = parser.parse_args().save_type
    return source_table, start_id,path_save, save_type

def initial_setup(source_table):
    path_error = f'errors/{source_table}.txt'
    df_bids=pd.read_csv('tables/lut_BIDS_14Dez23.csv')
    df_event = pd.read_excel(f'{source_table}.xlsx')
    root = 'bdsp/opendata/EEG/bids'
    windowsize = 15
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']

    return df_event,df_bids,root,windowsize,desired_channels,path_error

def investigate(data,Fs,path_error,startTime,eventTimes,HashFolderName,pathFolder,fileName):
    signal_t = data.shape[1]/Fs
    write_to_error(path_error, message='HashFolderName: ' + HashFolderName)
    write_to_error(path_error, message=f'Path folder: {pathFolder}')
    write_to_error(path_error, message=f'Filename: {fileName}')
    error_check = check_for_problems(path_error,folderPath,fileName,startTime,eventTimes,HashFolderName)
    write_to_error(path_error, message='Error check: '+error_check)

    write_to_error(path_error, message='Signal start time: '+ startTime.strftime('%Y-%m-%d %H:%M:%S'))
    write_to_error(path_error, message='Event times: ' + str([x.strftime('%Y-%m-%d %H:%M:%S') for x in eventTimes]))
    write_to_error(path_error, message=f'total signal duration: {signal_t/60:.1f} min')
    write_to_error(path_error, message=f'first event at: {(eventTimes[0]-startTime).total_seconds()/60:.1f} min into the recording')
    write_to_error(path_error, message=f'last event at:  {(eventTimes[-1]-startTime).total_seconds()/60:.1f} min into the recording\n')

if __name__ == '__main__':
    clear_cache()

    source_table, start_id,path_save, save_type = get_info_from_parser()
    df_event,df_bids,root,windowsize,desired_channels,path_error = initial_setup(source_table)


    for HashFolderName in tqdm(df_event.HashFolderName.unique()[start_id:20]):
        eventTimes = get_eventTimes(df_event,HashFolderName)
        folderPath,fileName, startTime = get_file_folder_and_name(df_bids,HashFolderName)
        #if check_for_problems(path_error,folderPath,fileName,startTime,eventTimes,HashFolderName) != 'OK': continue
        if not os.path.isdir(folderPath):
            write_to_error(path_error, message='Folder does not exist: ' + folderPath)
            continue

        if not os.path.isfile(os.path.join(folderPath,fileName)):
            write_to_error(path_error, message='File does not exist: ' + os.path.join(folderPath,fileName)+"\n")
            continue
        data,Fs = load_file(folderPath,fileName,desired_channels)
        path_log='log.txt'
        investigate(data,Fs,path_log,startTime,eventTimes,HashFolderName,folderPath,fileName)
        ###
        save_events(data,startTime,eventTimes,HashFolderName,windowsize,Fs,path_save,save_type=save_type)
        if set(eventTimes)-set(eventTimes)!=set():
            write_to_error(path_error, message='Not all events saved ' + HashFolderName)
        clear_cache()
