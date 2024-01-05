from viewer import *
# from utils import *
import matplotlib.pyplot as plt
import argparse
from tqdm import tqdm

# plt.switch_backend('TkAgg')  

bipolar_montage = init_montage_class(storage_channels = CDAC_monopolar_montage,
                                     montage_channels = CDAC_bipolar_montage+['None'],
                                     y_locations = -100*np.array([ 0,  1,  2,  3,
                                                                5,  6,  7,  8,
                                                                10, 11, 12, 13,
                                                                15, 16, 17, 18,
                                                                20, 21, 22]),
                                     y_labels = CDAC_bipolar_montage+[None]
                                     )
                                     
avg_montage = init_montage_class(storage_channels = CDAC_monopolar_montage,
                                     montage_channels = [c+'-avg' for c in CDAC_monopolar_montage],
                                     y_locations = -100*np.array([ 0,  1,  2,  3, 4, 5,  6,  7,
                                                                   9,  10, 11,  
                                                                   13, 14, 15, 16, 17, 18, 19, 20]),
                                     y_labels = [channel+'-avg' for channel in CDAC_monopolar_montage]
                                     )

action_list = {
    '1': lambda: (change_montage(ax,viewer_module=viewer_module,montage_module=montage_module),refresh_wrapped()),
    '+': lambda: (scaling_module.increase(),scale_module.increase_y_scale(),refresh_wrapped()),
    '-': lambda: (scaling_module.decrease(),scale_module.decrease_y_scale(),refresh_wrapped()),
    'right': lambda: (om.next(),refresh_wrapped()),
    'left': lambda: (om.prev(),refresh_wrapped()),
    'p': lambda:(fig.savefig(os.path.join(om.path_save,om.savenames[om.idx])))
    # More entries...
    }

def refresh(ax,overview_module,event_module,montage_module,scaling_module,viewer_module):
    path_event = om.path_files[om.idx]
    
    signal = event_module.load_event(path_event)  
    signal = montage_module(signal)
    signal = scaling_module(signal)
    update_channels_with_signal(signal=signal,
                                channel_lines=viewer_module.channel_lines,
                                y_locations=viewer_module.y_locations) 

    title = om.titles[om.idx]
    ax.set_title(title)
    fig.tight_layout()
    plt.draw()

if __name__=='__main__':    

    parser = argparse.ArgumentParser(description='Filter and sort DataFrame based on given criteria.')
    parser.add_argument('--path_files')
    parser.add_argument('--path_save',default='figures', help='path for storing images')
    parser.add_argument('--save',action='store_true')


    args = parser.parse_args()

    path_files = args.path_files
    
    path_signals = 'test' 
    path_save=args.path_save

    list_files = [f.replace('.npy','') for f in os.listdir(path_files)]
    list_events = [os.path.join(path_signals,f+'.npy') for f in list_files]
    list_titles = list_files    
    list_savenames = [f+'.png' for f in list_files]

    x_start = 0
    x_end = 15
    signal_start=0
    signal_end=15
    Fq = 128
    i = 0
    figsize = (12,9)

    # init the overview module
    om = init_overview_module(data={'path_files':list_events,
                                    'titles':list_titles,
                                    'path_save':path_save,
                                    'savenames': list_savenames})

    # init the montage module
    montage_module = init_montage_module(montages= [avg_montage,bipolar_montage])#+localized_montages)
    event_module= init_event_module(signal_start=signal_start, signal_end=signal_end,Fq=Fq)
    scaling_module = init_scaling_module(scaling_factor=1)

    # for each view, add a view to the subplot
    fig, ax = plt.subplots(1,1,figsize=figsize)
    y_labels = montage_module.montage.y_labels
    y_locations =montage_module.montage.y_locations
    ax.set_ylim([y_locations[-1]-100,y_locations[0]+100])
    viewer_module = init_viewer_module(ax=ax,x_start=x_start,x_end=x_end,y_labels=y_labels,Fq=Fq,y_locations=y_locations)
    scale_module = init_scale_module(ax)
    ax.set_xlim([0,15])

    # add some general axis specifications
    ax.set_xlabel('time [s]')

    # define the refresh function
    refresh_wrapped = lambda: refresh(ax=ax,
                                  overview_module=om,
                                  event_module=event_module,
                                  montage_module=montage_module,
                                  viewer_module=viewer_module,
                                  scaling_module=scaling_module)

    # connect the action function
    fig.canvas.mpl_connect('key_press_event',lambda event: action_list[event.key]())
    
    # if desired, save all files
    if args.save:
        for i in tqdm(range(len(om.path_files))):
            om.next(),refresh_wrapped(),fig.savefig(os.path.join(om.path_save,om.savenames[om.idx]))
        
    plt.show()