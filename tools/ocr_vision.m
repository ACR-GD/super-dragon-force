#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        for (int i = 1; i < argc; i++) {
            NSString *path = [NSString stringWithUTF8String:argv[i]];
            NSURL *url = [NSURL fileURLWithPath:path];
            VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithURL:url options:@{}];
            VNRecognizeTextRequest *req = [[VNRecognizeTextRequest alloc] init];
            req.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
            req.recognitionLanguages = @[@"zh-Hant", @"en-US"];
            req.usesLanguageCorrection = YES;
            NSError *err = nil;
            [handler performRequests:@[req] error:&err];
            if (err) {
                fprintf(stderr, "Error on %s: %s\n", argv[i], [[err localizedDescription] UTF8String]);
                continue;
            }
            for (VNRecognizedTextObservation *obs in req.results) {
                CGRect b = obs.boundingBox;
                NSArray<VNRecognizedText *> *cands = [obs topCandidates:3];
                NSMutableArray *arr = [NSMutableArray array];
                for (VNRecognizedText *c in cands) {
                    [arr addObject:@{@"text": c.string, @"conf": @(c.confidence)}];
                }
                NSDictionary *row = @{
                    @"file": path,
                    @"x": @(b.origin.x),
                    @"y": @(b.origin.y),
                    @"w": @(b.size.width),
                    @"h": @(b.size.height),
                    @"cands": arr
                };
                NSData *json = [NSJSONSerialization dataWithJSONObject:row options:0 error:nil];
                fwrite(json.bytes, 1, json.length, stdout);
                fputc('\n', stdout);
            }
        }
    }
    return 0;
}
