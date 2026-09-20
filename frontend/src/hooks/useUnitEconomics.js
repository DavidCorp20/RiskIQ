import { useMemo } from 'react'
const num=v=>Number.isFinite(Number(v))?Number(v):0
const balance=r=>num(r?.outstanding_principal??r?.outstanding_balance??r?.balance)
const rate=r=>num(r?.interest_rate??r?.annual_interest_rate??r?.yield??r?.rate)
const pd=r=>num(r?.pd??r?.probability_of_default)
const lgd=r=>num(r?.lgd??r?.loss_given_default)
const ead=r=>num(r?.ead??balance(r))
export function useUnitEconomics(rows=[],snapshot={}){return useMemo(()=>{const usable=rows.filter(r=>balance(r)>0);const totalExposure=usable.reduce((s,r)=>s+balance(r),0)||num(snapshot.outstanding_balance);const weightedRate=usable.reduce((s,r)=>s+rate(r)*balance(r),0);const yieldRate=totalExposure?weightedRate/totalExposure:0;const expectedLoss=usable.reduce((s,r)=>s+pd(r)*lgd(r)*ead(r),0);const cor=totalExposure?expectedLoss/totalExposure:0;const grossIncome=totalExposure*yieldRate;const riskCost=expectedLoss;return {totalExposure,yieldRate,expectedLoss,cor,grossIncome,riskCost,netRiskIncome:grossIncome-riskCost,raroc:null,hasYield:usable.some(r=>rate(r)>0),hasExpectedLoss:usable.some(r=>pd(r)>0&&lgd(r)>0)}},[rows,snapshot])}