export type SyntheticTrack={id:number;x:number;z:number;height:number};
export type SyntheticFrame={time:number;tracks:SyntheticTrack[]};
export type ImportedReplay={id:string;duration_sec:number;frames:SyntheticFrame[];annotations:{time:number;type:string;person_id:number;verified:false}[];provenance:{frame_sha256:string;note:string}};

// Latest actual supplied frame, without inventing interpolated coordinates.
export function importedFrameAt(frames:SyntheticFrame[],time:number):SyntheticFrame|null {
 if(!frames.length||!Number.isFinite(time)||time<0||time>frames[frames.length-1].time)return null;
 let low=0,high=frames.length-1,found=-1;
 while(low<=high){const mid=(low+high)>>>1;if(frames[mid].time<=time+1e-7){found=mid;low=mid+1;}else high=mid-1;}
 return frames[found]||null;
}
