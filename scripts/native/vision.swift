import Foundation
import Vision
import AppKit
import PDFKit
let args = CommandLine.arguments
func scan(_ cg: CGImage) throws -> [String:Any] {
 let text = VNRecognizeTextRequest();text.recognitionLevel = .accurate;text.usesLanguageCorrection=false
 let barcode = VNDetectBarcodesRequest();barcode.symbologies=[.qr]
 try VNImageRequestHandler(cgImage:cg).perform([text,barcode])
 let lines = (text.results ?? []).compactMap{$0.topCandidates(1).first}
 return ["text":lines.map{$0.string}.joined(separator:"\n"),"confidence":lines.map{Double($0.confidence)}.min() ?? 0,"qr":(barcode.results ?? []).compactMap{$0.payloadStringValue}]
}
do {
 if args.count < 3 { throw NSError(domain:"usage",code:1) }
 if args[1] == "pdf" {
  guard let doc=PDFDocument(url:URL(fileURLWithPath:args[2])) else {throw NSError(domain:"pdf",code:2)}
  var pages:[[String:Any]]=[]
  for i in 0..<doc.pageCount {
   let page=doc.page(at:i)!;let image=page.thumbnail(of:NSSize(width:1224,height:1584),for:.mediaBox)
   var bounds=NSRect(origin:.zero,size:image.size)
   guard let cg=image.cgImage(forProposedRect:&bounds,context:nil,hints:nil) else {continue}
   var result=try scan(cg);result["page"]=i+1;result["pdf_text"]=page.string ?? ""
   if args.count>3 {let rep=NSBitmapImageRep(cgImage:cg);try rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:args[3]+"-\(i+1).png"))}
   pages.append(result)
  }
  print(String(data:try JSONSerialization.data(withJSONObject:["pages":pages],options:[.sortedKeys]),encoding:.utf8)!)
 } else {
  guard let image=NSImage(contentsOfFile:args[2]) else {throw NSError(domain:"image",code:3)}
  var bounds=NSRect(origin:.zero,size:image.size)
  guard let cg=image.cgImage(forProposedRect:&bounds,context:nil,hints:nil) else {throw NSError(domain:"image",code:4)}
  print(String(data:try JSONSerialization.data(withJSONObject:scan(cg),options:[.sortedKeys]),encoding:.utf8)!)
 }
} catch {fputs("Unable to inspect document\n",stderr);exit(1)}
