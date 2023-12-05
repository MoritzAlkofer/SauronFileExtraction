import numpy as np
import matplotlib.pyplot as plt

def add_empty_line(ax,x_start,x_end,y,Fq):
    n_points = int((x_end-x_start)*Fq)
    return ax.plot((np.linspace(x_start,x_end,n_points)),([y]*n_points),'black',linewidth=0.7)

def add_scale(ax,x_start,x_end,y_start,y_end,x_label,y_label):
    # plot a scale on the ax object, going from x start to end and y start to end, with respective labels
    ax.plot((x_start,x_start),(y_start,y_end),'r')
    ax.text(x_start,y_end-40,y_label,c='r')
    ax.plot((x_start,x_end),(y_start,y_start),'r',)
    ax.text(x_end+0.1,y_start,x_label,c='r')

class init_transforms():
    def __init__(self,transforms={}):
        self.transforms = transforms
    def __call__(self,signal):
        for transform in self.transforms:
            signal = self.transforms[transform](signal)
        return signal

class init_montage_class():
    def __init__(self,view,views_list,storage_channels,montage_channels,montage):
        self.view = view
        self.views_list = views_list
        print(f'the following views are available: {views_list.keys()}')
        self.montage_channels = montage_channels
        self.montage = montage
    
    def __call__(self,signal):
        signal = self.montage(signal)

        keeper_indices = np.array([self.montage_channels.index(channel) for channel in self.views_list[self.view]])        
        output = np.zeros_like(signal)
        output[keeper_indices,:] = signal[keeper_indices,:]

        return output

def update_channels_with_signal(signal,channel_lines,y_locations):
    for i,line in enumerate(channel_lines):
        y_location = y_locations[i]
        data = signal[i,:]+y_location
        line.set_ydata(data)

def action_function(event,action_list, event_loader, montage_module, title_loader, viewer_module):
    action = action_list.get(event.key)
    action()

def change_view(viewer_module,event_loader,montage_module,title_loader,view):
    montage_module.view=view
    refresh(event_loader=event_loader,
            montage_module=montage_module,
            viewer_module=viewer_module,
            title_loader=title_loader)

def change_event_and_title(viewer_module,event_loader,title_loader,montage_module,increment):
    event_loader.idx+=increment
    title_loader.idx+=increment
    refresh(event_loader=event_loader,
            montage_module=montage_module,
            viewer_module=viewer_module,
            title_loader=title_loader)

def refresh(event_loader,montage_module,viewer_module,title_loader):
    signal = event_loader.load_event()        
    signal = montage_module(signal)
    update_channels_with_signal(signal=signal,
                                channel_lines=viewer_module.channel_lines,
                                y_locations=viewer_module.y_locations) 

    title = title_loader()
    viewer_module.ax.set_title(title)
    viewer_module.fig.tight_layout()

class init_event_loader():
    def __init__(self,path_events,list_events, signal_start = 2.5, signal_end = 12.5,Fq=128):
        self.path_event = path_events
        self.list_events = list_events
        self.idx = -1
        self.signal_start = signal_start
        self.signal_end = signal_end
        self.Fq=Fq

    def load_event(self):
        event_file = self.list_events[self.idx]
        signal = np.load(self.path_event+event_file+'.npy')
        signal = signal[:19,int(self.signal_start*self.Fq):int(self.signal_end*self.Fq)]
        return signal   



class init_viewer_module():
    def __init__(self,y_locations,y_labels,x_start,x_end,Fq,figsize=(10,7)):
        fig, ax = plt.subplots(figsize=figsize)

        # init empty lines 
        self.y_locations=y_locations
        self.fig = fig
        self.ax = ax 
        self.channel_lines = []
        for y_label,y_location in zip(y_labels,y_locations):
            line, = add_empty_line(ax,x_start=x_start,x_end=x_end,y=y_location,Fq = Fq)
            self.channel_lines.append(line)

        # add the scale
        add_scale(ax,x_start=0.5,x_end=1.5,y_start=0,y_end=-100,x_label='1s',y_label='100 ms')

        # set y axis ticks
        ax.set_yticks(y_locations,y_labels)
        ax.plot((5.25,5.25),(y_locations[0]+100,y_locations[-1]-100),'r','---',linewidth=0.5)
        ax.plot((4.75,4.75),(y_locations[0]+100,y_locations[-1]-100),'r','---',linewidth=0.5)

class build_montage():
    # this version can also convert cdac monopolar montage into mgh_psg monopolar montage
    def __init__(self,montage_channels,storage_channels,echo=True):
        
        # AVERAGE MONTAGE
        # get list of all channels that should be displayed in average montage
        avg_channels = [channel for channel in montage_channels if 'avg' in channel]
        # get ids of channels 

        self.avg_ids = np.array([storage_channels.index(channel.replace('-avg','')) for channel in avg_channels])

        # BIPOLAR MONTAGE
        # get list of all channels that should be displayed in average montage
        bipolar_channels = [channel for channel in montage_channels if ('avg' not in channel)&('-' in channel)]
        # get ids of channels 
        self.bipolar_ids = np.array([[storage_channels.index(channel.split('-')[0]), storage_channels.index(channel.split('-')[1])] for channel in bipolar_channels])
    
        # conversion
        # get list of all channels that should be displayed in average montage
        monopolar_channels = [channel for channel in montage_channels if ('avg' not in channel) and ('-' not in channel)]
        # get ids of channels 
        self.monopolar_ids = np.array([storage_channels.index(channel) for channel in monopolar_channels])
    
        if echo: print('storage channels: '+str(storage_channels))
        if echo: print('montage channels: '+str(avg_channels+bipolar_channels+monopolar_channels))

    def __call__(self,signal):
        signals = []
        # AVERAGE MONTAGE
        # get average of these signals along time axis
        if len(self.avg_ids>0):
            avg_signal = signal[self.avg_ids].mean(axis=0).squeeze()
            # substract average from original signal
            avg_montaged_signal = signal[self.avg_ids] - avg_signal
            signals.append(avg_montaged_signal)
        if len(self.bipolar_ids)>0:
            # BIPOLAR MONTAGE
            bipolar_montaged_signal = signal[self.bipolar_ids[:,0]] - signal[self.bipolar_ids[:,1]]
            signals.append(bipolar_montaged_signal)
        if len(self.monopolar_ids>0):
            # add monopolar channels
            signals.append(signal[self.monopolar_ids])

        signal = np.concatenate(signals)
        return signal

class init_title_loader_SauronEvent():
    def __init__(self,HashFolderNames,Classes,Annotations):
        self.HashFolderNames = HashFolderNames
        self.Classes = Classes
        self.Annotations = Annotations
        self.idx = -1

    def __call__(self):
        idx = self.idx
        title = 'HashFoldername: '+self.HashFolderNames[idx]+'\n Classes: '+self.Classes[idx]+'\n Annotations: '+self.Annotations[idx]+'\n'
        return title 

class init_title_loader_ChannelDeletionEval():
    def __init__(self,df):
        self.df = df
        self.idx = -1

    def __call__(self):
        title = self.df.iloc[self.idx]['event_file']+'\n'
        title = title+f'rater prediction: {self.df.iloc[self.idx]["fraction_of_yes"]:.2f}'+'\n\n'
        for channelLocation in ['frontalChannels','centralChannels', 'parietalChannels', 'occipitalChannels','temporalChannels']: 
            pred = self.df.iloc[self.idx][channelLocation]
            title = title + channelLocation +f': {pred:.2f}' + '\n'        
        return title