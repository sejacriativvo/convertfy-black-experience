// Rostos e corpos de cada quadro (Vision). Uso: pessoas <pasta_de_quadros>
// Saída, uma linha por quadro: arquivo|f cx cy w h;f ...|p cx cy w h;...  (normalizado, origem no canto superior esquerdo)
import Foundation
import Vision
import ImageIO

let pasta = URL(fileURLWithPath: CommandLine.arguments[1])
let nomes = try FileManager.default.contentsOfDirectory(atPath: pasta.path).filter { $0.hasSuffix(".jpg") }.sorted()
func fmt(_ b: CGRect) -> String { String(format: "%.4f %.4f %.4f %.4f", b.midX, 1 - b.midY, b.width, b.height) }
for nome in nomes {
    guard let src = CGImageSourceCreateWithURL(pasta.appendingPathComponent(nome) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { continue }
    let rostos = VNDetectFaceRectanglesRequest()
    let corpos = VNDetectHumanRectanglesRequest(); corpos.upperBodyOnly = false
    try? VNImageRequestHandler(cgImage: img).perform([rostos, corpos])
    let f = (rostos.results ?? []).map { fmt($0.boundingBox) }.joined(separator: ";")
    let p = (corpos.results ?? []).map { fmt($0.boundingBox) }.joined(separator: ";")
    print("\(nome)|\(f)|\(p)")
}
