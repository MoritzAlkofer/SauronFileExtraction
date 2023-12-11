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
        ecg_data = np.empty((1,data.shape[1]))
    data = np.vstack([eeg_data,ecg_data])
    return data

