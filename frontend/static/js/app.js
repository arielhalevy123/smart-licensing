window.DB = {
  licensingRequirements: [
    {id:1,title:"אישור משרד הבריאות",description:"בדיקות תברואה",business_types:["restaurant","cafe"],priority_level:"critical"},
    {id:2,title:"כיבוי אש",description:"מערכת ספרינקלרים",business_types:["restaurant","bar"],requires_gas:true,priority_level:"high"}
  ]
};

window.Utils = {
  save(key,obj){localStorage.setItem(key,JSON.stringify(obj));},
  load(key){try{return JSON.parse(localStorage.getItem(key));}catch{return null;}},
  matchRequirements(form){
    return DB.licensingRequirements.filter(r => r.business_types.includes(form.business_type));
  },
  async aiReport(form, matched){
    return {
      executive_summary:`נמצאו ${matched.length} דרישות לעסק מסוג ${form.business_type}.`,
      priority_requirements: matched.map(r=>r.title),
      recommendations:"להתחיל עם בריאות וכיבוי אש",
      estimated_timeline:"3 חודשים",
      estimated_total_cost:"₪20,000"
    };
  }
};