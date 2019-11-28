import numpy as np
import tables as tb
import logging
import numba
import time

import pixel_clusterizer.clusterizer as clusterizer

def clusterize_h5(fin,fout,col=2,row=2,frame=3,chunk_size=10000000, debug=1):
    t0=time.time()
    with tb.open_file(fin) as f:
        hits=f.root.Hits[:]
    hits['col']=hits['col']+1
    hits['row']=hits['row']+1
    hits['tot']=hits['tot']+1
    hit_fields={'event_number': 'event_number',  
                       'col': 'column',
                       'row': 'row',
                       'tot': 'charge',
                       'frame': 'frame'}
    clz = clusterizer.HitClusterizer(hit_fields=hit_fields,hit_dtype=hits.dtype,
         #cluster_fields=hit_fields,cluster_dtype=cluster_dtype,
         column_cluster_distance=col,row_cluster_distance=row,frame_cluster_distance=frame)
    #clz.set_end_of_cluster_function(end_of_cluster_function)

    # Main functions
    cluster_hits, clusters = clz.cluster_hits(hits)  # cluster hits
    hits=None # clear memory
    print "clusterize_h5() %.2fs # of clusters %d"%(time.time()-t0,len(cluster_hits))
    with tb.open_file(fout, "w") as f:
        if debug==1:
            cluster_hits_table=f.create_table(f.root,name="Hits",description=cluster_hits.dtype, title="Hits")
            start=0
            while start<len(cluster_hits):
                tmpend=min(start+chunk_size,len(cluster_hits))
                cluster_hits_table.append(cluster_hits[start:tmpend])
                cluster_hits_table.flush()
                start=tmpend
                print "clusterize_h5() %.2fs cluster_hits %.2f%% saved"%(
                        time.time()-t0,100.0*start/len(cluster_hits))

        clusters_table=f.create_table(f.root,name="Clusters",description=clusters.dtype, title="Clusters")
        start=0
        while start<len(clusters):
            tmpend=min(start+chunk_size,len(clusters))
            clusters_table.append(clusters[start:tmpend])
            clusters_table.flush()
            start=tmpend
            print "clusterize_h5() %.2fs clusters %.2f%% saved"%(
                    time.time()-t0,100.0*start/len(clusters))
    print "clusterize_h5() %.2fs DONE"%(time.time()-t0)