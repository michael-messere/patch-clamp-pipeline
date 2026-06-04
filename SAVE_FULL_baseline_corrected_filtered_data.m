function SAVE_FULL_baseline_corrected_filtered_data(mat_filename, Rsqrd, fcutoff_Butterworth, plotFlag)

    %% 
    %
    % objective: baseline-correct data. filter it. save both types of data.
    %
    % input arguments:
    % - mat_filename = filename with .mat extension, given in single quotes
    % - Rsqrd = noise guess for tds() baseline-correction function
    % - fcutoff_Butterworth = cutoff frequence in Hz, for filtered data
    % - plotFlag (0 = no plotting, 1 = yes plotting). 3 figures plotted.
    
	%%
    [~,name,ext] = fileparts(mat_filename);
    
    savename_baseline = 'baseline_data';
    savename_baseline_filtered = 'baseline_filt';
	%savename_IDout = 'ID';
    
	fsamp = 25000;
    
	disp('Generating and saving baseline-corrected data and filtered data...');
    
    %% Step 1. import raw data; append to array if multiple bin files per channel
    % dataimport = importdata([name, ext]);

    dataimport = load([name, ext]); 
    dataimport = dataimport.(char(fieldnames(dataimport)));
    if iscell(dataimport) == 1
	data = [];
	for i = 1 : length(dataimport)
		data = [data; dataimport{i}(:)];
	end
    else
	data = dataimport;
    end    

    %% Step 2. calculate and subtract out baseline
    bs = tds(Rsqrd, Rsqrd*(data - mean(data)));
    baseline_corrected_data = data - bs;
    % save it. 
	personalstruct = struct();        
	savename_str = [name, '_', savename_baseline];
	personalstruct.(savename_str) = baseline_corrected_data;
    personalstruct.([name, '_Rsqrd']) = Rsqrd;
	%save(savename_str, '-struct', 'personalstruct', savename_str);
    save(savename_str, '-struct', 'personalstruct');
    
    %% Step 3. filter data w/ 4th order, fc=1kHz Butterworth filter
    [b,a] = butter(4, fcutoff_Butterworth/(25000/2));
    baseline_corrected_filtered_data = filtfilt(b, a, baseline_corrected_data);
    % save it.
	personalstruct = struct();        
	savename_str = [name, '_', savename_baseline_filtered, '_', num2str(fcutoff_Butterworth), 'Hz'];
	personalstruct.(savename_str) = baseline_corrected_filtered_data;
    personalstruct.([savename_str, '_Rsqrd']) = Rsqrd;
	save(savename_str, '-struct', 'personalstruct');
    
    if plotFlag
        viewSecs_pre = 5;  % cursory, coarse view.
        manual_slider_plot({data, bs + mean(data)}, fsamp, viewSecs_pre);
        manual_slider_plot({baseline_corrected_data}, fsamp, viewSecs_pre);
        manual_slider_plot({baseline_corrected_filtered_data}, fsamp, viewSecs_pre);
    end

end
