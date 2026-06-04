function [bs] = tds(Rsqrd1, data1)

% adapted from "Automated maximum likelihood...", John Pearson paper
    main_d = (2+Rsqrd1)*ones(length(data1),1);
    main_d(1) = Rsqrd1+1;
    main_d(length(data1)) = Rsqrd1+1;
% main diagonal

    low_d = -ones(length(data1)-1,1);
    upper_d = low_d;
% upper and lower diagonals


% forward sweep
% rewrite the upper diagonal and rhs vector
    upper_d(1) = upper_d(1)/main_d(1);
    data1(1) = data1(1)/main_d(1);
% get the first component
    for rk = 2:length(upper_d)
        upper_d(rk) = upper_d(rk)./(main_d(rk)-low_d(rk-1)*upper_d(rk-1));
    end
    for rk = 2:length(data1)
        data1(rk) = (data1(rk)-low_d(rk-1)*data1(rk-1))/(main_d(rk)-low_d(rk-1)*upper_d(rk-1));
    end

% reverse sweep
% solve the system of equations
    %% SMT -- added explicit 'bs' variable definition
    bs = zeros(length(data1), 1);
    %%
    bs(length(data1)) = data1(length(data1));

    for rk = 1:length(data1)-1
        rrk = length(data1)-rk;
        bs(rrk) = data1(rrk)-upper_d(rrk)*bs(rrk+1);  
    end
    bs=bs(:);
% make the baseline
end
% invert finite difference operator