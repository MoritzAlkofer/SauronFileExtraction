

# for a given eeg file, generate the path to the .mat file
def generate_EEG_path(root,SiteID,EEGFolder,HashFolderName,index):
    # generate path to file and filename
    path = SiteID+'/'+EEGFolder+'/'+HashFolderName+'/'
    # insert 0 to create Hashfoldername_0_date_time
    # if next:
    #     eeg_start_time = eeg_start_time+timedelta(hours=12)
    #     index = 1
    eeg_start_time_str = datetime.strftime(eeg_start_time,'%Y%m%d_%H%M%S')
    filename = '_'.join([HashFolderName.split('_')[0],str(index),eeg_start_time_str])+'.mat'

    return os.path.join(root,filename)

def load_signal_and_data(path_file)
    # load signal and data
    signal = mat73.loadmat(path_file)
    data=signal['data']
    Fs=signal['Fs']
    channels=signal['channels']

    return data,Fs,channels