import numpy as np
import matplotlib.pyplot as plt

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
    
        # MONOPOLAR MONTAGE
        monopolar_channels = [channel for channel in montage_channels if ('avg' not in channel) and ('-' not in channel)and ('None' not in channel)]
        # get ids of channels 
        self.monopolar_ids = np.array([storage_channels.index(channel) for channel in monopolar_channels])

        # EMPTY LINES
        self.no_values = montage_channels.count('None')

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

        if self.no_values!=0:
            x = np.empty(shape=(self.no_values,signal.shape[1]))
            x[:] = np.nan
            signals.append(x)

        signal = np.concatenate(signals)
        return signal

class init_montage_class():
    def __init__(self,storage_channels,montage_channels,y_labels,y_locations):
        self.y_locations = y_locations
        self.y_labels = y_labels
        self.montage = build_montage(storage_channels=storage_channels,montage_channels=montage_channels)
    def __call__(self,signal):
        return self.montage(signal)
    
class init_montage_module:
    def __init__(self,montages):
        self.idx=0
        self.montages=montages
        self.montage=self.montages[self.idx]

    def __call__(self,signal):
        return self.montage(signal)

    def next_montage(self):
        self.idx = (self.idx+1)%(len(self.montages))
        self.montage = self.montages[self.idx]

def change_montage(viewer_module,montage_module):
    montage_module.next_montage()
    y_locations, y_labels = montage_module.montage.y_locations, montage_module.montage.y_labels

    viewer_module.y_locations = y_locations
    viewer_module.ax.set_yticks(y_locations,y_labels)

class init_scaling_module():
    def __init__(self,scaling_factor=1):
        self.scaling_factor=scaling_factor
    def increase(self):
        self.scaling_factor*=1.2
    def decrease(self):
        self.scaling_factor/=1.2

    def __call__(self,signal):
        return signal*self.scaling_factor

class init_title_module():
    def __init__(self,titles):
        self.titles = titles
        self.idx = -1

    def __call__(self):
        return self.titles[self.idx]
    def next(self):
        self.idx+=1
    def prev(self):
        self.idx-=1
        
class init_viewer_module():
    def __init__(self,y_locations,y_labels,x_start,x_end,Fq,figsize=(12,9)):
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
        # set y axis ticks
        ax.set_yticks(y_locations,y_labels)
        # ax.plot((5.25,5.25),(y_locations[0]+100,y_locations[-1]-100),'r','---',linewidth=0.5)
        # ax.plot((4.75,4.75),(y_locations[0]+100,y_locations[-1]-100),'r','---',linewidth=0.5)

class init_event_module():
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

    def next(self):
        self.idx+=1
    def prev(self):
        self.idx-=1

class init_scale_module():
    def __init__(self,ax,x_start=0.5,x_end=1.5,y_start=0,y_end=-100,x_label='1s',y_label='100 ms'):
        self.line_x_scale = ax.plot((x_start,x_end),(y_start,y_start),'r',)
        ax.text(x_end+0.1,y_start,x_label,c='r')
        self.line_y_scale, = ax.plot((x_start,x_start),(y_start,y_end),'r')
        ax.text(x_start,y_end-40,y_label,c='r')

        self.x_stary=x_start
        self.x_end=x_end
        self.y_start=y_start
        self.y_end=y_end

    def increase_y_scale(self):
        self.y_end*=1.2
        self.line_y_scale.set_ydata((self.y_start,self.y_end))

    def decrease_y_scale(self):
        self.y_end/=1.2
        self.line_y_scale.set_ydata((self.y_start,self.y_end))
    
def add_empty_line(ax,x_start,x_end,y,Fq):
    n_points = int((x_end-x_start)*Fq)
    return ax.plot((np.linspace(x_start,x_end,n_points)),([y]*n_points),'black',linewidth=0.7)

def change_event_and_title(viewer_module,event_module,title_module,montage_module,scaling_module,increment):
    event_module.idx+=increment
    title_module.idx+=increment
    refresh(event_module=event_module,
            montage_module=montage_module,
            viewer_module=viewer_module,
            title_module=title_module,
            scaling_module=scaling_module
            )

def update_channels_with_signal(signal,channel_lines,y_locations):
    for i,line in enumerate(channel_lines):
        y_location = y_locations[i]
        data = signal[i,:]+y_location
        line.set_ydata(data)

mgh_psg_mono_channels = ['F3', 'F4', 'C3', 'C4', 'O1', 'O2']
mgh_psg_avg_montage = ['F3-avg', 'F4-avg', 'C3-avg', 'C4-avg', 'O1-avg', 'O2-avg']
mgh_psg_bipolar_montage = ['F3-C3','C3-O1','F4-C4','C4-O2']

