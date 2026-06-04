function [t, data_nA] = load_data_nA_newGUI(channelNum) %, gain_Mohm)

    %
    % for use with Steve's revamped hardware & GUI code, mods of Scott's old hardware and GUI
    %

    channel_str = '';
  if channelNum < 10
        channel_str = ['0', num2str(channelNum)];
    else
        channel_str = num2str(channelNum);
    end
    
    myfile = dir(['*_Chan_', channel_str, '_*.bin']);
    
%     if length(myfile) == 1
%         fid = fopen(myfile.name);
%         binary_data = fread(fid, 'int16');
%         fclose(fid);
%     else
	binary_data = cell(length(myfile), 1);
	for i = 1 : length(myfile)
        fid = fopen(myfile(i).name);
        binary_data{i} = fread(fid, 'int16');
        fclose(fid);
	end
%     end
    
    %% pull DAC Voffset value from relevant channel from .param file
    paramfile = dir('*.param');
    fid = fopen(paramfile.name);
    breakFlag = 0;
    while ~breakFlag
        InputText = textscan(fid, '%s', 1, 'delimiter', '\n');
        if ~cellfun(@isempty, strfind(InputText{1}, ['Default vset (V) '])) 
            VoffsetStrSplit = strsplit(InputText{1}{1}, ' = ');
            V_DC_offset = str2double(VoffsetStrSplit{2});
            breakFlag = 1;
        end
    end    
    fclose(fid);
    
    %% pull ADC offset value from relevant channel from .param file
	fid = fopen(paramfile.name);
    breakFlag = 0;
    while ~breakFlag
        InputText = textscan(fid, '%s', 1, 'delimiter', '\n');
        if ~cellfun(@isempty, strfind(InputText{1}, ['ADC Offset ', num2str(channelNum), ' value'])) 
            ADCoffsetStrSplit = strsplit(InputText{1}{1}, ' = ');
            ADCoffset = str2double(ADCoffsetStrSplit{2});
            breakFlag = 1;
        end
    end
    fclose(fid);
    
    %% pull gain value for relevant channel from .param file
    paramfile = dir('*.param');
    fid = fopen(paramfile.name);
    breakFlag = 0;
    while ~breakFlag
        InputText = textscan(fid, '%s', 1, 'delimiter', '\n');
        if ~cellfun(@isempty, strfind(InputText{1}, ['Resistor ', num2str(channelNum), ' gain'])) 
            ResistorGainStrSplit = strsplit(InputText{1}{1}, ' = ');
            gain_Mohm = str2double(ResistorGainStrSplit{2});
            breakFlag = 1;
        end
    end    
    fclose(fid);
    
    %% pull hold value for relevant channel from .param file
	paramfile = dir('*.param');
    fid = fopen(paramfile.name);
    breakFlag = 0;
    while ~breakFlag
        InputText = textscan(fid, '%s', 1, 'delimiter', '\n');
        if ~cellfun(@isempty, strfind(InputText{1}, ['HOLD ', num2str(channelNum), ' value'])) 
            HoldStrSplit = strsplit(InputText{1}{1}, ' = ');
            Vhold = str2double(HoldStrSplit{2});
            breakFlag = 1;
        end
    end    
    fclose(fid);
    
    %% pull ResX value for relevant channel from .param file
	paramfile = dir('*.param');
    fid = fopen(paramfile.name);
    breakFlag = 0;
    while ~breakFlag
        InputText = textscan(fid, '%s', 1, 'delimiter', '\n');
        if ~cellfun(@isempty, strfind(InputText{1}, ['HOLD ', num2str(channelNum), ' value'])) 
            HoldStrSplit = strsplit(InputText{1}{1}, ' = ');
            Vhold = str2double(HoldStrSplit{2});
            breakFlag = 1;
        end
    end    
    fclose(fid);
    
    %% convert binary data to nA, and give time vector as well
    vdd = 5.0;
    bits = 14;
    fsample = 25000;        % 40 u
    
	for i = 1 : length(binary_data)
        data = (binary_data{i} * vdd ./ (2^bits - 1)) + V_DC_offset;
        data_A = (data - V_DC_offset - ADCoffset - Vhold) ./ (gain_Mohm * 1e6);
        data_nA{i} = data_A * 1e9;
        t{i} = 0 : (1/fsample) : length(data_nA{i})/fsample - (1/fsample);
            
        t{i} = t{i}(:);
        data_nA{i} = data_nA{i}(:);
    end
    
    % convert single files back from cell to array
    if length(binary_data) == 1
        t = cell2mat(t);
        data_nA = cell2mat(data_nA);
        
        t = t(:);
        data_nA = data_nA(:);
    end
    
end

%% old stuff

%     paramfile = dir('.*param');
%     fid = fopen(paramfile.name);
%     numLines_experimentInfo = 10;
%     % read in first 10 lines before 'Resistor X...' string (on line 11)
%     textscan(fid, '%s', numLines_experimentInfo, 'delimiter', '\n');
%     breakFlag = 0;
% 	%while ~feof(fid)
%     while ~breakFlag
%         ResistorGainNum = textscan(fid, 'Resistor %f gain (Mohm) = %f', 1, 'delimiter', '\n');
%         if ResistorGainNum{1} == channelNum
%             gain_Mohm = ResistorGainNum{2};
%             breakFlag = 1;
%         end
%     end
%     fclose(fid);
    
%     paramfile = dir('*.param');
%     fid = fopen(paramfile.name);
%     A = textscan(fid, '%s', 'delimiter', '\n');
%     A = A{1};   % take 1st (and only, for that matter) cell element
%     B = strfind(A, [num2str(channelNum), ' gain']);
%     nonemptycellindex = ~cellfun(@isempty,B);
%     line_str = cell2mat(A(nonemptycellindex));
%     gain_Mohm = strsplit(line_str, ' = ');
%     gain_Mohm = str2double(gain_Mohm(2));
%     fclose(fid);