$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = $true
$pres = $pp.Presentations.Add()

# Helper to add a slide with title and image
define-slide {
    param(
        [int]$index,
        [string]$title,
        [string]$imagePath
    )
    $slide = $pres.Slides.Add($index, 12) # ppLayoutBlank = 12
    # Add title textbox
    $shape = $slide.Shapes.AddTextbox(1, 20, 20, 700, 40) # msoTextOrientationHorizontal = 1
    $shape.TextFrame.TextRange.Text = $title
    $shape.TextFrame.TextRange.Font.Size = 24
    $shape.TextFrame.TextRange.Font.Bold = $true
    # Add picture
    $slide.Shapes.AddPicture($imagePath, $false, $true, 50, 80, 800, 450) | Out-Null
}

# Paths to screenshots (use forward slashes for PowerShell)
$img1 = "C:/Users/pavan kalyan/.gemini/antigravity/brain/cd6b5d22-0371-4310-9057-a0a5b5791567/.user_uploaded/media_1795083649950_ba56fd97.png"
$img2 = "C:/Users/pavan kalyan/.gemini/antigravity/brain/cd6b5d22-0371-4310-9057-a0a5b5791567/browser_evidence/d0072b11-3188-4131-a9a3-3a614b8f75e6/final_step_6.png"
$img3 = "C:/Users/pavan kalyan/.gemini/antigravity/brain/cd6b5d22-0371-4310-9057-a0a5b5791567/browser_evidence/d0072b11-3188-4131-a9a3-3a614b8f75e6/final_step_19.png"

# Create 6 slides (some reuse images with different titles)
define-slide -index 1 -title "DataFix.ai – Enterprise Dashboard" -imagePath $img1

define-slide -index 2 -title "High‑Contrast Headings & KPI Cards" -imagePath $img2

define-slide -index 3 -title "New Premium Buttons & Sidebar" -imagePath $img3

# Add placeholder slides for remaining topics
$slide4 = $pres.Slides.Add(4,12)
$shape4 = $slide4.Shapes.AddTextbox(1,20,20,700,40)
$shape4.TextFrame.TextRange.Text = "Issue Detection & Radar Chart"
$shape4.TextFrame.TextRange.Font.Size = 24
$shape4.TextFrame.TextRange.Font.Bold = $true

$slide5 = $pres.Slides.Add(5,12)
$shape5 = $slide5.Shapes.AddTextbox(1,20,20,700,40)
$shape5.TextFrame.TextRange.Text = "Root‑Cause Analysis & Repair Engine"
$shape5.TextFrame.TextRange.Font.Size = 24
$shape5.TextFrame.TextRange.Font.Bold = $true

$slide6 = $pres.Slides.Add(6,12)
$shape6 = $slide6.Shapes.AddTextbox(1,20,20,700,40)
$shape6.TextFrame.TextRange.Text = "Export Suite & Audit Log"
$shape6.TextFrame.TextRange.Font.Size = 24
$shape6.TextFrame.TextRange.Font.Bold = $true

# Save presentation
$savePath = "C:/Users/pavan kalyan/New folder (3)/CareerAI/DataFixPresentation.pptx"
$pres.SaveAs($savePath)
$pp.Quit()
