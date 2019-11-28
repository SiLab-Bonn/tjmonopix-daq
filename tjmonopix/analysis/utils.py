import numpy as np
import matplotlib.pyplot as plt
from scipy.special import erf
from scipy.optimize import curve_fit, leastsq

def scurve(x, A, mu, sigma):
    return 0.5*A*erf((x-mu)/(np.sqrt(2)*sigma))+0.5*A

def scurve_rev(x, A, mu, sigma):
    return 0.5*A*erf((mu-x)/(np.sqrt(2)*sigma))+0.5*A

    
    
def fit_scurve1(xarray,yarray,A=None,cut_ratio=0.05,reverse=True,debug=0):
    if A is None:
        A=np.max(yarray)
        
    if reverse==True:
        arg=np.argsort(xarray)[::-1]
    else:
        arg=np.argsort(xarray)
    yarray=yarray[arg]
    xarray=xarray[arg]
    if debug==1:
        plt.plot(xarray,yarray,".")
        
    #### cut
    no_cut=np.argwhere(yarray>A*(1-cut_ratio))
    if len(no_cut)==0:
        cut=len(xarray) ## if there are no data higher than A*0.95 then take all data
    else:
        no_cut=no_cut[0][0] 
        cut_high=np.argwhere(yarray[no_cut:]>=A*(1+cut_ratio))
        if len(cut_high)==0:
            cut=len(xarray) # if there are no data higher than A*1.05, then take all data
        else:
            cut=no_cut+cut_high[0][0]
        cut_low=np.argwhere(yarray[no_cut:cut]<A*(1-2*cut_ratio))
        if len(cut_low)>0:
            cut=min(no_cut+cut_low[0][0],cut)
    yarray=yarray[:cut]
    xarray=xarray[:cut]
    if debug:
         print no_cut,cut, xarray,yarray
        
    mu=xarray[np.argmin(np.abs(yarray-A*0.5))]
    try:
        sig2=xarray[np.argwhere(yarray>A*cut_ratio)[0]][0]
        sig1=xarray[np.argwhere(yarray>A*(1-cut_ratio))[0]][0]
        sigma=abs(sig1-sig2)/3.5
    except:
        if debug==1:
            print('estimation of simga did not work')
        sigma=1
    if debug==1:
        print "estimation",A,mu,sigma

    if debug==1:
        plt.plot(xarray,yarray,"o")
        if reverse:
            plt.plot(xarray,scurve_rev(xarray,A,mu,sigma),"--")
        else:
            plt.plot(xarray,scurve(xarray,A,mu,sigma),"--")
    try:
        if reverse:
            p,cov = curve_fit(scurve_rev, xarray, yarray, p0=[A,mu,sigma])
        else:
            p,cov = curve_fit(scurve, xarray, yarray, p0=[A,mu,sigma])
    except RuntimeError:
        if debug==2:
            print('fit did not work',xarray,yarray)
        return A,mu,sigma,float("nan"),float("nan"),float("nan")
    err=np.sqrt(np.diag(cov))
    return p[0],p[1],p[2],err[0],err[1],err[2]
    
    
    
def fit_scurve(xarray,yarray,A=None,cut_ratio=0.05,reverse=True,debug=0):
    if A is None:
        A=np.max(yarray)
        
    if reverse==True:
        arg=np.argsort(xarray)[::-1]
    else:
        arg=np.argsort(xarray)
    yarray=yarray[arg]
    xarray=xarray[arg]
    if debug==1:
        plt.plot(xarray,yarray,"r.")
        
    #### cut
    cut=len(xarray)
    cut_low=np.argwhere(yarray>=A*(1-cut_ratio))
    if len(cut_low)>0:
        no_cut=cut_low[0][0]
        if cut_low[-1][0] > 1:
            cut=cut_low[-1][0]
    if debug==1:
        print cut,
        plt.plot(xarray[:cut],yarray[:cut],"b.")
    cut_high=np.argwhere(yarray>=A*(1+cut_ratio))    
    if len(cut_high)>0:
        if cut_high[0][0] > no_cut:
            cut=min(cut_high[0][0], cut)
    yarray=yarray[:cut]
    xarray=xarray[:cut]
    mu=xarray[np.argmin(np.abs(yarray-A*0.5))]
    try:
        sig2=xarray[np.argwhere(yarray>A*cut_ratio)[0]][0]
        sig1=xarray[np.argwhere(yarray>A*(1-cut_ratio))[0]][0]
        #print('estimation of simga did not work')
        sigma=abs(sig1-sig2)/3.5
    except:
        sigma=1
    if debug==1:
        print "estimation",A,mu,sigma

    if debug==1:
        plt.plot(xarray,yarray,"o")
        plt.plot(xarray,scurve_rev(xarray,A,mu,sigma),"--")
    try:
        if reverse:
            p,cov = curve_fit(scurve_rev, xarray, yarray, p0=[A,mu,sigma])
        else:
            p,cov = curve_fit(scurve, xarray, yarray, p0=[A,mu,sigma])
    except RuntimeError:
        if debug==2:
            print('fit did not work')
        return A,mu,sigma,float("nan"),float("nan"),float("nan")
    err=np.sqrt(np.diag(cov))
    return p[0],p[1],p[2],err[0],err[1],err[2]
    
def scurve_from_fit(th, A_fit,mu_fit,sigma_fit,reverse=True,n=500):
    th_min=np.min(th)
    th_max=np.max(th)
    x=np.arange(th_min,th_max,(th_max-th_min)/float(n))
    if reverse:
        return x,scurve_rev(x,A_fit,mu_fit,sigma_fit)
    else:
        return x,scurve(x,A_fit,mu_fit,sigma_fit)
