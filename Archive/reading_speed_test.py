import pandas as pd
import os
from pyedflib import EdfReader
import numpy as np
import h5py
from tqdm import tqdm
from time import time

def write_to_error(path_error,message,echo=False):
    # if an error occurs, write it to errors.txt
    with open(path_error, 'a') as f:
        f.write(message+'\n')
        f.close()
    if echo:
        print(message)

def initial_setup(batch_id):
    path_error = f'errors/batch{batch_id}.txt'
    df=pd.read_csv(f'tables/batch{batch_id}.csv')
    root = 'bdsp/opendata/EEG/bids'
    windowsize = 15
    desired_channels= ['Fp1','F3','C3','P3','F7','T3','T5','O1','Fz','Cz','Pz','Fp2','F4','C4','P4','F8','T4','T6','O2']

    return df,root,windowsize,desired_channels,path_error

def get_folder_name(df,bdsp_patient_id):
    foldername = 'sub-'+df[df.bdsp_patient_id==bdsp_patient_id].site_code.iloc[0]+str(bdsp_patient_id)
    return foldername

def correct_file_in_folder(root,foldername,ses):
    files = [f for f in os.listdir(root+'/'+foldername+'/'+ses+'/eeg') if f.endswith('.edf')]
    if len(files)>1:
        write_to_error(path_error, message='More than one .edf in: ' + foldername + ' ' + ses)
        return False
    if len(files)==0:
        write_to_error(path_error, message='More than one .edf in: ' + foldername + ' ' + ses)
        return False
    else :
        return True

def get_filename(root,foldername,ses):
    files = [f for f in os.listdir(root+'/'+foldername+'/'+ses+'/eeg') if f.endswith('.edf')]
    return files[0]

def get_ecg_data(edf, start, n):
    labels = edf.getSignalLabels()
    if 'ECGL' in labels:
        ecg = edf.readSignal(labels.index('ECGL'), start, n) - edf.readsignal(labels.index('ECGR'), start, n)
    elif 'EKG1' in labels:
        ecg = edf.readSignal(labels.index('EKG1'), start, n) - edf.readsignal(labels.index('EKG2'), start, n)  
    elif 'EKG' in labels:
        ecg = edf.readSignal(labels.index('EKG'), start, n)
    else:
        ecg = np.empty(n)

    return ecg

def edf_check(path_edf,desired_labels):
    try:
        with EdfReader(path_edf) as edf:
            labels = edf.getSignalLabels()
            if set(desired_labels).issubset(set(labels)):
                return True
            else:
                write_to_error(path_error, message='not all channels present ' + path_edf)
                return False
    except:
        write_to_error(path_error, message='edf not readable ' + path_edf)
        return False

def read_edf(path_edf, desired_channels, timestamp, windowsize):
    with EdfReader(path_edf) as edf:
        desired_ids = [edf.getSignalLabels().index(c) for c in desired_channels]
        Fs = edf.getSampleFrequency(desired_ids[0])
        start = int(Fs*(timestamp - windowsize//2))
        n = int(Fs*windowsize)
        eeg_data = [edf.readSignal(id,start=start,n=n) for id in desired_ids]
        labels = edf.getSignalLabels()
        if 'ECGL' in labels:
            ecg_data = edf.readSignal(labels.index('ECGL'), start, n) - edf.readSignal(labels.index('ECGR'), start, n)
        elif 'EKG1' in labels:
            ecg_data = edf.readSignal(labels.index('EKG1'), start, n) - edf.readSignal(labels.index('EKG2'), start, n)  
        elif 'EKG' in labels:
            ecg_data = edf.readSignal(labels.index('EKG'), start, n)
        else:
            ecg_data = np.empty(n)
    # list ecg to fix dimensionality
        data = np.concatenate([eeg_data, [ecg_data]], axis=0)
    return data

def get_save_name(bdsp_patient_id,ses,timestamp):
    savename = f'{bdsp_patient_id}_{ses}_{timestamp}'
    return savename

def signal_check(signal,name):
    if np.isnan(signal).all():
        write_to_error(path_error, message='event is allnan ' + name)
        return False
    if signal.shape[1] != 3000:
        write_to_error(path_error, message='signal len != 3000 ts' + name)
        return False
    else: 
        return True

def save_event_as_h5(path_save,name,signal):
        # Save in an HDF5 file
        with h5py.File(path_save, 'a') as hf:
            if name not in hf:
                hf.create_dataset(name, data=signal, dtype='f4')
            else:
                write_to_error(path_error, message=f'Dataset already exists in the HDF5 file. {name}')

def save_event_as_npy(path_save,name,signal):
    np.save(path_save+name,signal)

batch = '001'
df,root,windowsize,desired_channels,path_error = initial_setup(batch)

times = []
for bdsp_patient_id in tqdm([df.bdsp_patient_id.unique()[7]]):
    folderName = get_folder_name(df,bdsp_patient_id)
    for ses in df[df.bdsp_patient_id==bdsp_patient_id].bids_session.unique():
        if correct_file_in_folder(root,folderName,ses) == False:
            continue
        fileName = get_filename(root,folderName,ses)
        path_edf = os.path.join(root,folderName,ses,'eeg',fileName)
        if edf_check(path_edf,desired_channels) == False:
            continue
        for timestamp in tqdm(df[(df.bdsp_patient_id==bdsp_patient_id)&(df.bids_session==ses)].annotation_time_offset_sec.unique(),leave=False):
            t = time()
            signal = read_edf(path_edf, desired_channels, timestamp, windowsize)
            read_time = time()-t
            times.append(read_time)