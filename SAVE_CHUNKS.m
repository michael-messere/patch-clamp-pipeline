function SAVE_CHUNKS(mat_filename, bias_str, numChunks)

    %% static value declarations
    savename_filt = ['bias_', bias_str];
    
    %% load data
    [~, name, ext] = fileparts(mat_filename);
    data = importdata([name, ext]);
    data = data.(name);
    
    %% split data into 5 chunks (60 seconds worth  per chunk)
    chunks = reshape(data, [], numChunks);
    chunk = cell(numChunks, 1);
    for i = 1 : numChunks
        chunk{i} = chunks(:,i);
    end
    
	%% save filtered chunks, if I haven't already created the save file
    for i = 1 : numChunks
        savename_str = [name, '_', savename_filt, '_chunk', num2str(i)];
        if exist([savename_str, '.mat'], 'file') ~= 2
            personalstruct = struct();
            personalstruct.(savename_str) = chunk{i};
            save(savename_str, '-struct', 'personalstruct');
        end
    end   

end