import React, { useState, useEffect } from 'react';
import { 
  Upload, CheckCircle, AlertTriangle, Play, HelpCircle, 
  Layers, Check, ChevronRight, FileSpreadsheet, FileText, ZoomIn, ZoomOut
} from 'lucide-react';
import UploadStep from './workflow/UploadStep';
import ClassifyStep from './workflow/ClassifyStep';
import ExtractStep from './workflow/ExtractStep';
import LoadingOverlay from './common/LoadingOverlay';
import VerifyStep from './workflow/VerifyStep';
import BoqStep from './workflow/BoqStep';

export default function Workflow({ token, project, isArabic, onNavigate }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [loadingSubtext, setLoadingSubtext] = useState('');
  const [message, setMessage] = useState('');
  
  // File Upload State
  const [strFiles, setStrFiles] = useState([]);
  const [archFiles, setArchFiles] = useState([]);
  const [uploadResult, setUploadResult] = useState(null);
  
  // Classification State
  const [classifiedPages, setClassifiedPages] = useState([]);
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  
  // Extraction State
  const [extractionResults, setExtractionResults] = useState(null);
  
  // Confirm/Verify State
  const [confirmedData, setConfirmedData] = useState({
    longest_length: 0,
    longest_width: 0,
    plot_area: 0,
    gf_area: 0,
    ext_perimeter: 0,
    roof_perimeter: 0,
    roof_slab_area: 0,
    compound_length: 0,
    total_villa_height: 0,
    parapet_height: 1.0,
    excavation_depth: 1.25,
    neck_column_height: 1.0,
    solid_block_height: 1.0,
    staircase_volume_per_level: 5.2,
    schedules: {},
    floors: {},
    walls: {},
    openings: {}
  });
  
  // Calculation Parameters
  const [calcParams, setCalcParams] = useState({
    num_floors: 2,
    gf_height: 4.0,
    f1_height: 4.0,
    f2_height: 4.0,
    excavation_depth: 1.25,
    include_road_base: true,
    concrete_grade: "C30/37",
    solid_block_thickness: "200mm",
    thermal_block_thickness: "200mm",
    hollow_block_thickness: "100mm"
  });
  
  // Review / BOQ Items
  const [boqItems, setBoqItems] = useState([]);
  const [boqMeta, setBoqMeta] = useState({ needs_input: [], estimates: [] });
  const [sanityWarnings, setSanityWarnings] = useState([]);
  
  // UI States
  const [zoom, setZoom] = useState(1);
  const [acknowledgedEstimates, setAcknowledgedEstimates] = useState(false);

  const renderSourceBadge = (fieldName) => {
    const source = confirmedData.sources?.[fieldName] || '';
    if (!source) return null;
    
    let badgeColor = '#3b82f6'; // blue for AI
    let bgColor = '#eff6ff';
    let confidence = '85%';
    
    if (source.includes('Verified')) {
      badgeColor = '#10b981'; // green for user verified
      bgColor = '#ecfdf5';
      confidence = '100%';
    } else if (source.includes('CV')) {
      badgeColor = '#8b5cf6'; // purple for CV
      bgColor = '#f5f3ff';
      confidence = '70%';
    } else if (source.includes('Fallback') || source.includes('Heuristic')) {
      badgeColor = '#f59e0b'; // orange for math fallback/estimates
      bgColor = '#fffbeb';
      confidence = '50%';
    } else if (source.includes('Default')) {
      badgeColor = '#6b7280'; // gray for default
      bgColor = '#f3f4f6';
      confidence = '90%';
    }
    
    return (
      <span style={{ 
        marginLeft: '8px', 
        padding: '2px 6px', 
        borderRadius: '4px', 
        fontSize: '0.7rem', 
        fontWeight: 600,
        color: badgeColor,
        backgroundColor: bgColor,
        border: `1.5px solid ${badgeColor}`
      }}>
        {source} ({confidence})
      </span>
    );
  };

  const updateConfirmedField = (fieldName, value) => {
    setConfirmedData(prev => {
      const updated = { ...prev };
      updated[fieldName] = value;
      if (!updated.sources) updated.sources = {};
      updated.sources[fieldName] = "User Verified";
      if (fieldName === 'compound_length') {
        updated.compound_length_is_estimated = false;
      }
      return updated;
    });
  };

  const updateOpeningField = (subField, value) => {
    setConfirmedData(prev => {
      const updated = { ...prev };
      if (!updated.openings) updated.openings = {};
      if (!updated.openings.totals) updated.openings.totals = {};
      updated.openings.totals[subField] = value;
      
      if (!updated.sources) updated.sources = {};
      updated.sources[subField] = "User Verified";
      
      if (subField === 'door_count') {
        updated.openings.totals.door_count_is_estimated = false;
      } else if (subField === 'window_area') {
        updated.openings.totals.window_area_is_estimated = false;
      }
      return updated;
    });
  };

  const hasEstimates = !!(confirmedData.compound_length_is_estimated ||
                       confirmedData.openings?.totals?.door_count_is_estimated || 
                       confirmedData.openings?.totals?.window_area_is_estimated);

  const API_URL = "/api/workflow";

  useEffect(() => {
    // If project already has some state, load it
    if (project) {
      setCurrentStep(project.current_step || 1);
      fetchActiveState();
    }
  }, [project]);

  const fetchActiveState = async () => {
    try {
      const res = await fetch("/api/projects/active", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.has_active && data.state_data) {
        const state = typeof data.state_data === 'string' ? JSON.parse(data.state_data) : data.state_data;
        if (state.classified_pages) setClassifiedPages(state.classified_pages);
        if (state.extraction_results) setExtractionResults(state.extraction_results);
        if (state.confirmed_auto_data) {
          setConfirmedData(prev => ({ 
            ...prev, 
            excavation_depth: 1.25,
            neck_column_height: 1.0,
            solid_block_height: 1.0,
            staircase_volume_per_level: 5.2,
            ...state.confirmed_auto_data 
          }));
        }
        if (state.boq_items) setBoqItems(state.boq_items);
        if (state.boq_meta) setBoqMeta(state.boq_meta);
        if (state.num_floors) setCalcParams(prev => ({
          ...prev,
          num_floors: state.num_floors,
          gf_height: state.gf_height || 4.0,
          f1_height: state.f1_height || 4.0,
          f2_height: state.f2_height || 4.0,
          excavation_depth: state.excavation_depth || 1.25,
          include_road_base: state.include_road_base !== false,
          concrete_grade: state.concrete_grade || "C30/37",
          solid_block_thickness: state.solid_block_thickness || "200mm",
          thermal_block_thickness: state.thermal_block_thickness || "200mm",
          hollow_block_thickness: state.hollow_block_thickness || "100mm"
        }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const saveActiveState = async (step, overrideState = {}) => {
    try {
      const stateToSave = {
        project_id: project.id,
        project_name: project.name,
        current_step: step,
        classified_pages: classifiedPages,
        extraction_results: extractionResults,
        confirmed_auto_data: confirmedData,
        boq_items: boqItems,
        boq_meta: boqMeta,
        ...calcParams,
        ...overrideState
      };
      
      await fetch("/api/projects", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.id,
          project_name: project.name,
          current_step: step,
          state_data: stateToSave,
          boq_data: { items: boqItems.filter(item => !item._is_header) }
        })
      });
    } catch (err) {
      console.error(err);
    }
  };

  // Step 1: Upload Files
  const handleUpload = async (e) => {
    e.preventDefault();
    if ((strFiles.length === 0 && archFiles.length === 0) || loading) return;

    setLoading(true);
    setLoadingText(isArabic ? 'جاري قراءة المخططات...' : 'Uploading & Processing Blueprints...');
    setLoadingSubtext(isArabic ? 'يرجى الانتظار بينما نقوم بتحليل الصفحات...' : 'Please wait while we parse the pages...');
    setMessage('');
    
    const formData = new FormData();
    formData.append('project_id', project.id);
    strFiles.forEach(f => formData.append('str_files', f));
    archFiles.forEach(f => formData.append('arch_files', f));

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed.');
      
      setUploadResult(data);
      setMessage(isArabic ? 'تم رفع المخططات وتقسيمها بنجاح!' : 'Drawings uploaded and page images cached successfully!');
      
      // Auto run classification
      handleAutoClassify();
    } catch (err) {
      setMessage(`Error: ${err.message}`);
      setLoading(false);
    }
  };

  // Step 2: Auto Classify
  const handleAutoClassify = async () => {
    setLoading(true);
    setLoadingText(isArabic ? 'جاري تصنيف الصفحات...' : 'Classifying Pages...');
    setLoadingSubtext(isArabic ? 'يقوم الذكاء الاصطناعي بالتعرف على نوع كل صفحة...' : 'AI is analyzing and identifying each drawing type...');
    try {
      const res = await fetch(`${API_URL}/classify/auto`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: project.id })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Auto classification failed.');
      
      setClassifiedPages(data.classified_pages || []);
      setCurrentStep(2);
      await saveActiveState(2, { classified_pages: data.classified_pages });
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveClassifications = async () => {
    setLoading(true);
    setLoadingText(isArabic ? 'جاري الحفظ...' : 'Saving Classifications...');
    setLoadingSubtext('');
    try {
      const res = await fetch(`${API_URL}/classify/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.id,
          classified_pages: classifiedPages
        })
      });
      if (!res.ok) throw new Error('Failed to save classifications.');
      
      setCurrentStep(3);
      await saveActiveState(3);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  const [extractionProgress, setExtractionProgress] = useState(null);

  // Step 3: Run AI Extraction
  const handleRunExtraction = async () => {
    setLoading(true);
    setExtractionProgress(0);
    setLoadingText(isArabic ? 'جاري الاستخراج بالذكاء الاصطناعي...' : 'AI Extraction in Progress...');
    setLoadingSubtext(isArabic ? 'هذه العملية قد تستغرق دقيقة. جاري استخراج الجداول والأبعاد...' : 'This might take a minute. Extracting schedules and dimensions...');
    setMessage('');
    try {
      const res = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: project.id })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'AI extraction failed.');
      }
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let isStreamDone = false;
      let buffer = '';

      while (!isStreamDone) {
        const { value, done } = await reader.read();
        isStreamDone = done;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // keep the last incomplete chunk in buffer
          
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                
                if (data.progress !== undefined) {
                  setExtractionProgress(data.progress);
                }
                if (data.status) {
                  setLoadingSubtext(data.status);
                }
                if (data.done) {
                  setExtractionResults(data.extraction_results);
                  
                  // Parse extraction results into default confirmed data model
                  const confirmedObj = { 
                    ...confirmedData,
                    floors: { ...(confirmedData.floors || {}) },
                    walls: { ...(confirmedData.walls || {}) },
                    schedules: { ...(confirmedData.schedules || {}) },
                    openings: { ...(confirmedData.openings || {}) }
                  };
                  
                  const floorMap = {
                    "ground_floor_plan": "gf",
                    "first_floor_plan": "1f",
                    "second_floor_plan": "2f",
                    "roof_floor_plan": "roof"
                  };

                  confirmedObj.total_doors_count = 0;
                  confirmedObj.total_windows_area = 0;

                  Object.values(data.extraction_results).forEach(page => {
                    if (!page._ok) return;
                    
                    const dtype = page.drawing_type || page.detected_type;

                    if (page.longest_length) confirmedObj.longest_length = page.longest_length;
                    if (page.longest_width) confirmedObj.longest_width = page.longest_width;
                    if (page.plot_area) confirmedObj.plot_area = page.plot_area;
                    if (page.compound_length) confirmedObj.compound_length = page.compound_length;
                    if (page.total_villa_height) confirmedObj.total_villa_height = page.total_villa_height;
                    
                    if (dtype === "ground_floor_plan") {
                      if (page.total_floor_area) confirmedObj.gf_area = page.total_floor_area;
                      if (page.ext_perimeter) confirmedObj.ext_perimeter = page.ext_perimeter;
                      if (page.int_walls_length) confirmedObj.int_walls_length = page.int_walls_length;
                      if (page.int_walls_10cm_m !== undefined) confirmedObj.int_walls_10cm_m = page.int_walls_10cm_m;
                      if (page.int_walls_20cm_m !== undefined) confirmedObj.int_walls_20cm_m = page.int_walls_20cm_m;
                    }

                    if (["ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan"].includes(dtype)) {
                      if (page.total_doors_count !== undefined) {
                        confirmedObj.total_doors_count = (confirmedObj.total_doors_count || 0) + page.total_doors_count;
                      }
                      if (page.total_windows_area !== undefined) {
                        confirmedObj.total_windows_area = (confirmedObj.total_windows_area || 0) + page.total_windows_area;
                      }
                    }

                    if (dtype === "roof_floor_plan" || dtype === "roof_slab") {
                      if (page.roof_perimeter) confirmedObj.roof_perimeter = page.roof_perimeter;
                      if (page.slab_area) confirmedObj.roof_slab_area = page.slab_area;
                    }
                    
                    if (floorMap[dtype]) {
                      const fk = floorMap[dtype];
                      confirmedObj.floors[fk] = {
                        area: page.total_floor_area || page.floor_area || 0.0,
                        ext_perimeter: page.ext_perimeter || 0.0,
                        wet_area: page.wet_area || 0.0,
                        wet_perimeter: page.wet_perimeter || 0.0,
                        dry_perimeter: page.dry_perimeter || 0.0,
                        balcony_area: page.balcony_area || page.balcony_terrace_area_m2 || 0.0,
                        height: page.floor_height || 4.0
                      };
                      
                      confirmedObj.walls[fk] = {
                        internal_total_m: page.int_walls_length || 0.0,
                        internal_10cm_m: page.int_walls_10cm_m || 0.0,
                        internal_20cm_m: page.int_walls_20cm_m || 0.0
                      };
                    }

                    if (page.footings) {
                      confirmedObj.schedules.foundation = { footings: page.footings };
                    }
                    if (page.beams) {
                      confirmedObj.schedules[dtype] = { beams: page.beams };
                    }
                    if (page.columns) {
                      confirmedObj.schedules.column_schedule = { columns: page.columns };
                    }
                    if (page.doors || page.windows) {
                      if (page.doors) confirmedObj.openings.doors = page.doors;
                      if (page.windows) confirmedObj.openings.windows = page.windows;
                    }
                  });
                  
                  setConfirmedData(confirmedObj);
                  setCurrentStep(4);
                  await saveActiveState(4, { extraction_results: data.extraction_results, confirmed_auto_data: confirmedObj });
                  
                  setLoading(false);
                  setExtractionProgress(null);
                  isStreamDone = true; // explicitly break
                }
              } catch (e) {
                console.error("Error parsing SSE chunk:", e, line);
              }
            }
          }
        }
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
      setLoading(false);
      setExtractionProgress(null);
    }
  };

  // Step 4: Confirm parsed variables
  const handleConfirmDataSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoadingText(isArabic ? 'جاري حفظ التأكيد...' : 'Saving Verified Data...');
    setLoadingSubtext('');
    try {
      const res = await fetch(`${API_URL}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.id,
          confirmed_data: confirmedData
        })
      });
      if (!res.ok) throw new Error('Failed to save confirmation data.');
      
      setCurrentStep(5);
      await saveActiveState(5);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Step 5: Execute BOQ Calculation
  const handleRunCalculation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setLoadingText(isArabic ? 'جاري الحساب الهندسي...' : 'Running Engineering Calculations...');
    setLoadingSubtext(isArabic ? 'نقوم الآن بتطبيق معادلات حصر الكميات وبناء جدول الكميات...' : 'Applying QS formulas and building the BOQ...');
    try {
      const res = await fetch(`${API_URL}/calculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.id,
          ...calcParams
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Calculation engine failed.');
      
      // Inject pricing columns if not present
      const pricedItems = data.boq_items.map(item => {
        if (item._is_header) return item;
        return {
          ...item,
          "Unit Price": item["Unit Price"] !== undefined ? parseFloat(item["Unit Price"]) : 0.0,
          "Total": item["Total"] !== undefined ? parseFloat(item["Total"]) : 0.0
        };
      });

      setBoqItems(pricedItems);
      setBoqMeta(data.boq_meta);
      setCurrentStep(6);
      await saveActiveState(6, { boq_items: pricedItems, boq_meta: data.boq_meta });
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Step 6: Review Pricing and quantities
  const handlePriceChange = (index, priceVal) => {
    const price = parseFloat(priceVal) || 0.0;
    setBoqItems(prev => {
      const updated = [...prev];
      const qty = parseFloat(updated[index]["Quantity"]) || 0.0;
      updated[index]["Unit Price"] = price;
      updated[index]["Total"] = qty * price;
      return updated;
    });
  };

  const handleQtyChange = (index, qtyVal) => {
    const qty = parseFloat(qtyVal);
    setBoqItems(prev => {
      const updated = [...prev];
      updated[index]["Quantity"] = isNaN(qty) ? 0 : qty;
      updated[index].has_error = false;   // a manual edit clears the calc-error flag
      const price = parseFloat(updated[index]["Unit Price"]) || 0.0;
      updated[index]["Total"] = (isNaN(qty) ? 0 : qty) * price;
      return updated;
    });
  };

  const calculateGrandTotal = () => {
    return boqItems.reduce((acc, item) => {
      if (item._is_header) return acc;
      return acc + (parseFloat(item["Total"]) || 0.0);
    }, 0.0);
  };

  const handleSaveReview = async () => {
    setLoading(true);
    setLoadingText(isArabic ? 'جاري الحفظ...' : 'Saving Review...');
    try {
      const res = await fetch(`${API_URL}/review/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: project.id,
          boq_items: boqItems
        })
      });
      if (!res.ok) throw new Error('Failed to save quantities review.');
      
      setCurrentStep(8); // Proceed directly to download
      await saveActiveState(8);
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Exporters
  const downloadExcel = () => {
    window.open(`/api/workflow/export/excel?project_id=${project.id}&Authorization=Bearer ${token}`);
  };

  const downloadPDF = () => {
    window.open(`/api/workflow/export/pdf?project_id=${project.id}&Authorization=Bearer ${token}`);
  };

  // UI Helpers
  const stepIcons = {
    1: <Upload size={16} />,
    2: <Layers size={16} />,
    3: <Play size={16} />,
    4: <Check size={16} />,
    5: <Layers size={16} />,
    6: <FileText size={16} />,
    7: <Layers size={16} />,
    8: <FileSpreadsheet size={16} />
  };

  const stepLabels = {
    1: { en: 'Upload', ar: 'رفع المخططات' },
    2: { en: 'Classify', ar: 'تصنيف الصفحات' },
    3: { en: 'Extract', ar: 'استخراج بالذكاء' },
    4: { en: 'Confirm', ar: 'تأكيد الحقول' },
    5: { en: 'Equations', ar: 'تطبيق المعادلات' },
    6: { en: 'Review BOQ', ar: 'مراجعة الأسعار' },
    7: { en: 'Arrange', ar: 'ترتيب البنود' },
    8: { en: 'Download', ar: 'تحميل التقارير' }
  };

  return (
    <div style={{ position: 'relative', width: '100%', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <LoadingOverlay 
        isLoading={loading} 
        text={loadingText} 
        subtext={loadingSubtext}
        progress={extractionProgress}
        isArabic={isArabic} 
      />
      
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', direction: isArabic ? 'rtl' : 'ltr', textAlign: isArabic ? 'right' : 'left' }}>
      
      {/* 8-Step Header Indicator */}
      <div className="glass-panel" style={{ margin: '20px 30px', padding: '15px 20px', display: 'flex', justifyContent: 'space-between', gap: '8px', overflowX: 'auto' }}>
        {[1, 2, 3, 4, 5, 6, 7, 8].map((num) => {
          const isActive = num === currentStep;
          const isDone = num < currentStep;
          return (
            <div 
              key={num} 
              onClick={() => isDone && setCurrentStep(num)}
              style={{
                flex: 1,
                minWidth: '95px',
                padding: '8px 4px',
                borderRadius: '12px',
                textAlign: 'center',
                background: isActive ? 'linear-gradient(135deg, var(--primary), var(--primary-hover))' : isDone ? 'rgba(16, 185, 129, 0.08)' : 'var(--bg-primary)',
                border: isActive ? 'none' : isDone ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-color)',
                color: isActive ? 'white' : isDone ? 'var(--success)' : 'var(--text-secondary)',
                cursor: isDone ? 'pointer' : 'default',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                boxShadow: isActive ? '0 4px 12px var(--primary-glow)' : 'none',
                transition: 'all 0.3s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {isDone ? <CheckCircle size={14} /> : stepIcons[num]}
                <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{num}</span>
              </div>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, display: 'block', whiteSpace: 'nowrap' }}>
                {isArabic ? stepLabels[num].ar : stepLabels[num].en}
              </span>
            </div>
          );
        })}
      </div>

      {message && (
        <div style={{ margin: '0 30px 20px', padding: '12px 16px', backgroundColor: 'rgba(59,130,246,0.1)', color: 'var(--primary)', borderRadius: '8px', fontSize: '0.9rem' }}>
          {message}
        </div>
      )}

        {/* Steps Content Area */}
      <div style={{ flex: 1, padding: '0 30px 30px' }}>
        {currentStep === 1 && (
          <UploadStep
            strFiles={strFiles}
            setStrFiles={setStrFiles}
            archFiles={archFiles}
            setArchFiles={setArchFiles}
            loading={loading}
            handleUpload={handleUpload}
            isArabic={isArabic}
          />
        )}
        {currentStep === 2 && (
          <ClassifyStep
            classifiedPages={classifiedPages}
            setClassifiedPages={setClassifiedPages}
            selectedPageIndex={selectedPageIndex}
            setSelectedPageIndex={setSelectedPageIndex}
            zoom={zoom}
            setZoom={setZoom}
            isArabic={isArabic}
            handleSaveClassifications={handleSaveClassifications}
            loading={loading}
          />
        )}
        {currentStep === 3 && (
          <ExtractStep
            loading={loading}
            isArabic={isArabic}
            handleRunExtraction={handleRunExtraction}
          />
        )}
        {(currentStep === 4 || currentStep === 5) && (
          <VerifyStep
            currentStep={currentStep}
            confirmedData={confirmedData}
            sanityWarnings={sanityWarnings}
            updateConfirmedField={updateConfirmedField}
            updateOpeningField={updateOpeningField}
            renderSourceBadge={renderSourceBadge}
            extractionResults={extractionResults}
            hasEstimates={hasEstimates}
            acknowledgedEstimates={acknowledgedEstimates}
            setAcknowledgedEstimates={setAcknowledgedEstimates}
            handleConfirmDataSubmit={handleConfirmDataSubmit}
            calcParams={calcParams}
            setCalcParams={setCalcParams}
            handleRunCalculation={handleRunCalculation}
            loading={loading}
            isArabic={isArabic}
          />
        )}
        {(currentStep === 6 || currentStep === 8) && (
          <BoqStep
            currentStep={currentStep}
            boqMeta={boqMeta}
            calculateGrandTotal={calculateGrandTotal}
            boqItems={boqItems}
            handlePriceChange={handlePriceChange}
            handleQtyChange={handleQtyChange}
            handleSaveReview={handleSaveReview}
            setCurrentStep={setCurrentStep}
            downloadExcel={downloadExcel}
            downloadPDF={downloadPDF}
            onNavigate={onNavigate}
            isArabic={isArabic}
          />
        )}
      </div>
    </div>
    </div>
  );
}
