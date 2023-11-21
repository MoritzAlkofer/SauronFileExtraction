import mat73
from datetime import datetime
import numpy as np

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

def get_event_snippet(data,relative_event_time,windowsize,all_channels,desired_channels,Fs):
    # takes a piece of signal of shape [channel, ts], the timestamp of the event and the windowsize
    # returns the event pm windowsize, shape [channel, windowsize]
    
    snippet_start = int((relative_event_time-windowsize/2)*Fs)
    snippet_end = int((relative_event_time+windowsize/2)*Fs)
    desired_channel_ids = [all_channels.index(channel) for channel in desired_channels]
    return data[desired_channel_ids,snippet_start:snippet_end]

def process_EEG_file(root,SiteID,EEGFolder,HashFolderName):
    # generate path to file and filename
    path = SiteID+'/'+EEGFolder+'/'+HashFolderName+'/'
    # insert 0 to create Hashfoldername_0_date_time
    filename = '_'.join([HashFolderName.split('_')[0],'0']+HashFolderName.split('_')[1:3])+'.mat'

    # load signal and data
    signal = mat73.loadmat(root+path+filename)
    data=signal['data']
    Fs=signal['Fs']
    channels=signal['channels']
    absolute_start_time = get_time_from_filename(filename)

    return data,Fs,channels,absolute_start_time