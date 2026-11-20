import { useState, useEffect } from 'react';
import { 
  Upload, CheckCircle, Play, 
  Layers, Check, FileSpreadsheet, FileText
} from 'lucide-react';
import UploadStep from './workflow/UploadStep';
import ClassifyStep from './workflow/ClassifyStep';
import ExtractStep from './workflow/ExtractStep';
import LoadingOverlay from './common/LoadingOverlay';
import VerifyStep from './workflow/VerifyStep';
import BoqStep from './workflow/BoqStep';
import FeedbackModal from './common/FeedbackModal';

const API_URL = "/api/workflow";

export default function Workflow({ token, project, isArabic, onNavigate }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('');
  const [loadingSubtext, setLoadingSubtext] = useState('');
  const [message, setMessage] = useState('');
  
  // File Upload State
  const [strFiles, setStrFiles] = useState([]);
  const [archFiles, setArchFiles] = useState([]);
  
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
    hollow_block_thickness: "100mm",
    // Roof stair-room handling for the top floor (auto-detected, user-editable)
    top_floor_is_stair_room: false,
    stair_room_area: "",
    stair_room_perimeter: ""
  });
  
  // Review / BOQ Items
  const [boqItems, setBoqItems] = useState([]);
  const [boqMeta, setBoqMeta] = useState({ needs_input: [], estimates: [] });
  const [sanityWarnings, setSanityWarnings] = useState([]);
  
  const [showFeedback, setShowFeedback] = useState(false);
  
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
      const updated = {
        ...prev,
        openings: {
          ...(prev.openings || {}),
          totals: { ...(prev.openings?.totals || {}) }
        },
        sources: { ...(prev.sources || {}) }
      };
      updated.openings.totals[subField] = value;
      updated.sources[subField] = "User Verified";
      
      if (subField === 'door_count') {
        const parsedDoors = parseInt(value) || 0;
        updated.openings.totals.door_count_is_estimated = false;
        updated.openings.totals.user_edited_door_count = true;
        updated.openings.user_override_door_count = parsedDoors;
        updated.total_doors_count = parsedDoors;
      } else if (subField === 'window_area') {
        const parsedWin = parseFloat(value) || 0;
        updated.openings.totals.window_area_is_estimated = false;
        updated.openings.totals.user_edited_window_area = true;
        updated.openings.user_override_window_area = parsedWin;
        updated.total_windows_area = parsedWin;
      }
      return updated;
    });
  };

  const hasEstimates = !!(confirmedData.compound_length_is_estimated ||
                       confirmedData.openings?.totals?.door_count_is_estimated || 
                       confirmedData.openings?.totals?.window_area_is_estimated);

  const projectId = project?.id;

  useEffect(() => {
    if (!projectId) return;
    let active = true;
    (async () => {
      try {
        const res = await fetch(`${API_URL}/projects/active?project_id=${projectId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!active || !res.ok) return;
        const text = await res.text();
        if (!active || !text) return;
        let data = null;
        try { data = JSON.parse(text); } catch { return; }
        if (data.has_active && data.state_data) {
          const state = typeof data.state_data === 'string' ? JSON.parse(data.state_data) : data.state_data;
          if (state.classified_pages) setClassifiedPages(state.classified_pages);
          if (state.extraction_results) setExtractionResults(state.extraction_results);
          if (state.sanity_warnings) setSanityWarnings(state.sanity_warnings);
          if (state.confirmed_auto_data) {
            setConfirmedData(prev => ({ 
              ...prev, 
              excavation_depth: 1.25,
              neck_column_height: 1.0,
              solid_block_height: 1.0,
              staircase_volume_per_level: 5.2,
              sog_thickness: 0.10,
              default_col_length: 0.60,
              default_col_width: 0.20,
              ...state.confirmed_auto_data 
            }));
          }
          if (state.boq_items) setBoqItems(state.boq_items);
          if (state.boq_meta) setBoqMeta(state.boq_meta);
          // Pre-fill the auto-detected roof stair-room flag for the top floor.
          {
            const cad = state.confirmed_auto_data || {};
            const ftypes = cad.floor_types || state.floor_types || {};
            const fls = cad.floors || {};
            const nf = state.num_floors || (fls['2f'] ? 3 : (fls['1f'] ? 2 : (cad.structural_levels || 2)));
            const topFk = nf >= 3 ? '2f' : '1f';
            const topIsStair = ftypes[topFk] === 'stair_room';
            const topFloor = fls[topFk] || {};
            const extGfH = Number(state.gf_height || cad.gf_height || fls.gf?.height || 0);
            const extF1H = Number(state.f1_height || cad.f1_height || fls['1f']?.height || 0);
            const extF2H = Number(state.f2_height || cad.f2_height || fls['2f']?.height || 0);
            setCalcParams(prev => ({
              ...prev,
              num_floors: nf,
              gf_height: (extGfH >= 2.5 && extGfH <= 6.5) ? extGfH : prev.gf_height,
              f1_height: (extF1H >= 2.5 && extF1H <= 6.5) ? extF1H : prev.f1_height,
              f2_height: (extF2H >= 2.5 && extF2H <= 6.5) ? extF2H : prev.f2_height,
              top_floor_is_stair_room: topIsStair,
              stair_room_area: (topIsStair && topFloor.is_stair_room) ? (topFloor.area ?? '') : prev.stair_room_area,
              stair_room_perimeter: (topIsStair && topFloor.is_stair_room) ? (topFloor.ext_perimeter ?? '') : prev.stair_room_perimeter,
            }));
          }
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
    })();
    return () => { active = false; };
  }, [projectId, token]);

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
    setMessage('');

    const safeJsonFetch = async (url, options = {}) => {
      const res = await fetch(url, options);
      const text = await res.text();
      let data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch { /* ignore non-JSON body */ }
      }
      if (!res.ok) {
        const msg = data?.detail || (res.status === 504 ? (isArabic ? 'انتهت مهلة استجابة الخادم (504). يرجى المحاولة مجدداً.' : 'Server gateway timeout (504). Please try again.') : (isArabic ? `فشل طلب الخادم (رمز ${res.status}).` : `Server request failed (HTTP ${res.status}).`));
        throw new Error(msg);
      }
      if (!data) {
        throw new Error(isArabic ? `تنسيق رد غير صالح من الخادم (رمز ${res.status}).` : `Invalid response format from server (HTTP ${res.status}).`);
      }
      return data;
    };

    try {
      const formData = new FormData();
      formData.append('project_id', project.id);
      
      let hasStr = false;
      if (strFiles.length > 0) {
        hasStr = true;
        strFiles.forEach(f => formData.append('str_files', f));
      }
      
      let hasArch = false;
      if (archFiles.length > 0) {
        hasArch = true;
        archFiles.forEach(f => formData.append('arch_files', f));
      }
      
      if (hasStr || hasArch) {
        setLoadingSubtext(isArabic ? 'جاري رفع المخططات (الإنشائية والمعمارية)...' : 'Uploading Drawings (Structural & Architectural)...');
        await safeJsonFetch(`${API_URL}/upload`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        });
      }
      
      setMessage(isArabic ? 'تم رفع المخططات وتقسيمها بنجاح!' : 'Drawings uploaded successfully!');
      
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
      const safeJsonFetch = async (url, options = {}) => {
        const res = await fetch(url, options);
        const text = await res.text();
        let data = null;
        if (text) {
          try { data = JSON.parse(text); } catch { /* ignore non-JSON body */ }
        }
        if (!res.ok) {
          const msg = data?.detail || (res.status === 504 ? (isArabic ? 'انتهت مهلة استجابة الخادم أثناء التصنيف (504).' : 'Server gateway timeout during classification (504).') : `Server error (HTTP ${res.status})`);
          throw new Error(msg);
        }
        if (!data) throw new Error(`Invalid response format from server (HTTP ${res.status}).`);
        return data;
      };

      const data = await safeJsonFetch(`${API_URL}/classify/auto`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: project.id })
      });
      
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
      const cleanPages = (classifiedPages || []).map(p => ({
        pdf: p.pdf || 'structural',
        page_index: Number(p.page_index) || 0,
        page_num: Number(p.page_num) || 1,
        text_preview: (p.text_preview || '').slice(0, 200),
        detected_type: p.detected_type || 'unknown',
        confidence: p.confidence || 'low',
        items: Array.isArray(p.items) ? p.items : []
      }));

      const res = await fetch(`${API_URL}/classify/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: Number(project.id),
          classified_pages: cleanPages
        })
      });
      const text = await res.text();
      let data = null;
      if (text) {
        try { data = JSON.parse(text); } catch { /* ignore non-JSON body */ }
      }
      if (!res.ok) {
        throw new Error(data?.detail || (isArabic ? 'فشل حفظ التصنيفات.' : 'Failed to save classifications.'));
      }
      
      setCurrentStep(3);
      await saveActiveState(3, { classified_pages: cleanPages });
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
        let errorMsg = 'AI extraction failed.';
        try {
          const text = await res.text();
          if (text) {
            const errJson = JSON.parse(text);
            errorMsg = errJson.detail || errorMsg;
          }
        } catch {
          errorMsg = res.status === 504 ? (isArabic ? 'انتهت مهلة خادم الاستخراج (504). يرجى المحاولة مجدداً.' : 'Extraction request timed out (504). Please try again.') : `Server Error (HTTP ${res.status})`;
        }
        throw new Error(errorMsg);
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

                  // Prefer the backend-healed confirmed_auto_data (includes geometric fallbacks,
                  // CV heuristics, and all reconstruct_project_inputs healing). Fall back to
                  // parsing raw extraction_results only if the backend didn't return healed data.
                  let confirmedObj;
                  if (data.confirmed_auto_data && Object.keys(data.confirmed_auto_data).length > 0) {
                    confirmedObj = {
                      ...confirmedData,
                      ...data.confirmed_auto_data,
                      floors: { ...(confirmedData.floors || {}), ...(data.confirmed_auto_data.floors || {}) },
                      walls: { ...(confirmedData.walls || {}), ...(data.confirmed_auto_data.walls || {}) },
                      schedules: { ...(confirmedData.schedules || {}), ...(data.confirmed_auto_data.schedules || {}) },
                      openings: data.confirmed_auto_data.openings || confirmedData.openings || {},
                    };
                    // Map openings totals to flat fields expected by VerifyStep
                    const totals = confirmedObj.openings?.totals || {};
                    if (totals.door_count !== undefined) confirmedObj.total_doors_count = totals.door_count;
                    if (totals.window_area !== undefined) confirmedObj.total_windows_area = totals.window_area;
                  } else {
                    // Fallback: parse raw extraction results manually
                    confirmedObj = {
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
                  }

                  setConfirmedData(confirmedObj);
                  setSanityWarnings(data.sanity_warnings || []);
                  // Pre-fill auto-detected floor heights, floor count, and roof stair-room flag
                  {
                    const ftypes = confirmedObj.floor_types || {};
                    const fls = confirmedObj.floors || {};
                    const detectedLevels = fls['2f'] ? 3 : (fls['1f'] ? 2 : (confirmedObj.structural_levels || calcParams.num_floors || 2));
                    const topFk = detectedLevels >= 3 ? '2f' : '1f';
                    const topIsStair = ftypes[topFk] === 'stair_room';
                    const topFloor = fls[topFk] || {};
                    const extGfH = Number(confirmedObj.gf_height || fls.gf?.height || 0);
                    const extF1H = Number(confirmedObj.f1_height || fls['1f']?.height || 0);
                    const extF2H = Number(confirmedObj.f2_height || fls['2f']?.height || 0);
                    setCalcParams(prev => ({
                      ...prev,
                      num_floors: detectedLevels,
                      gf_height: (extGfH >= 2.5 && extGfH <= 6.5) ? extGfH : prev.gf_height,
                      f1_height: (extF1H >= 2.5 && extF1H <= 6.5) ? extF1H : prev.f1_height,
                      f2_height: (extF2H >= 2.5 && extF2H <= 6.5) ? extF2H : prev.f2_height,
                      top_floor_is_stair_room: topIsStair,
                      stair_room_area: (topIsStair && topFloor.is_stair_room) ? (topFloor.area ?? '') : prev.stair_room_area,
                      stair_room_perimeter: (topIsStair && topFloor.is_stair_room) ? (topFloor.ext_perimeter ?? '') : prev.stair_room_perimeter,
                    }));
                  }
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
          ...calcParams,
          // Send null (not "") for blank stair-room dims so the backend uses its
          // auto value; pydantic floats reject empty strings.
          stair_room_area: calcParams.stair_room_area === "" || calcParams.stair_room_area == null ? null : parseFloat(calcParams.stair_room_area),
          stair_room_perimeter: calcParams.stair_room_perimeter === "" || calcParams.stair_room_perimeter == null ? null : parseFloat(calcParams.stair_room_perimeter),
          top_floor_is_stair_room: !!calcParams.top_floor_is_stair_room
        })
      });
      const text = await res.text();
      let data = null;
      if (text) {
        try { data = JSON.parse(text); } catch { /* ignore non-JSON body */ }
      }
      if (!res.ok) throw new Error(data?.detail || 'Calculation engine failed.');
      if (!data) throw new Error('Calculation engine returned an invalid response.');
      
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

  // Exporters (authenticated fetch + Blob download so JWT never leaks in URL query params)
  const downloadAuthenticatedFile = async (endpoint, fallbackFilename) => {
    try {
      const res = await fetch(`${API_URL}${endpoint}?project_id=${project.id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) {
        let errMsg = `Export failed (${res.status})`;
        try {
          const errJson = await res.json();
          if (errJson?.detail) errMsg = errJson.detail;
        } catch {
          // Ignore non-JSON error body
        }
        alert(errMsg);
        return;
      }
      const blob = await res.blob();
      let filename = fallbackFilename;
      const disp = res.headers.get('Content-Disposition') || '';
      const match = disp.match(/filename="?([^";]+)"?/i);
      if (match?.[1]) filename = match[1];
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setShowFeedback(true);
    } catch (err) {
      alert(err.message);
    }
  };

  const downloadExcel = () => downloadAuthenticatedFile('/export/excel', `${project.name || 'Project'}_BOQ.xlsx`);
  const downloadPDF = () => downloadAuthenticatedFile('/export/pdf', `${project.name || 'Project'}_BOQ.pdf`);

  // UI Helpers
  const stepIcons = {
    1: <Upload size={16} />,
    2: <Layers size={16} />,
    3: <Play size={16} />,
    4: <Check size={16} />,
    5: <Layers size={16} />,
    6: <FileText size={16} />,
    8: <FileSpreadsheet size={16} />
  };

  const stepLabels = {
    1: { en: 'Upload', ar: 'رفع المخططات' },
    2: { en: 'Classify', ar: 'تصنيف الصفحات' },
    3: { en: 'Extract', ar: 'استخراج بالذكاء' },
    4: { en: 'Confirm', ar: 'تأكيد الحقول' },
    5: { en: 'Equations', ar: 'تطبيق المعادلات' },
    6: { en: 'Review BOQ', ar: 'مراجعة الأسعار' },
    8: { en: 'Download', ar: 'تحميل التقارير' }
  };

  const effectiveStep = currentStep === 7 ? 8 : currentStep;

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
      
      {/* 7-Step Header Indicator (maps to backend steps 1-6 and 8) */}
      <div className="glass-panel" style={{ margin: '20px 30px', padding: '15px 20px', display: 'flex', justifyContent: 'space-between', gap: '8px', overflowX: 'auto' }}>
        {[1, 2, 3, 4, 5, 6, 8].map((num, idx) => {
          const isActive = num === effectiveStep;
          const isDone = num < effectiveStep;
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
                <span style={{ fontSize: '0.85rem', fontWeight: 700 }}>{idx + 1}</span>
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
        {effectiveStep >= 6 && (
          <BoqStep
            currentStep={effectiveStep}
            boqMeta={boqMeta}
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
      
      <FeedbackModal 
        isOpen={showFeedback} 
        onClose={() => setShowFeedback(false)} 
        toolName="QTO Workflow" 
        projectName={project ? project.name : ''} 
        isArabic={isArabic} 
      />
    </div>
    </div>
  );
}
